"""Intel Social Track-1 collector — Apify actors for LinkedIn + Twitter/X scraping.

Reads company_linkedin_url and twitter_handle from the intel-company upstream result
(context.upstream_results["intel-company"]) — NOT from template vars.

Both are optional: if Apify is not configured, or if the upstream URLs are missing,
or if the Apify API call fails, this collector returns empty post lists (non-fatal).
Track 2 (LLM) still runs and can produce a signal_summary from zero posts.

Apify actor calls are synchronous HTTP POSTs (REST API) via httpx.
Each actor is called with a JSON input, and the run result is polled until done.
"""

from __future__ import annotations

from typing import Any

import structlog

from prism_platform.config import settings
from prism_platform.v2.types import ExecutionContextV2

logger = structlog.get_logger(__name__)

# Apify REST API base URL
_APIFY_BASE = "https://api.apify.com/v2"

# Actor IDs — stable Apify public actors
_LINKEDIN_ACTOR = "apify/linkedin-company-posts-scraper"
_TWITTER_ACTOR = "apify/twitter-scraper"

# Maximum posts to collect per platform
_MAX_POSTS = 10

# Poll interval and timeout for Apify run completion (seconds)
_POLL_INTERVAL = 3.0
_RUN_TIMEOUT = 60.0


def _extract_company_social_urls(upstream_intel_company: dict[str, Any]) -> tuple[str, str]:
    """Extract linkedin_url and twitter_handle from the intel-company output dict.

    Returns (linkedin_url, twitter_handle) — either may be empty string.
    Handles both nested and flat output shapes defensively.
    """
    linkedin_url = (
        upstream_intel_company.get("company_linkedin_url")
        or upstream_intel_company.get("linkedin_url")
        or ""
    )
    twitter_handle = (
        upstream_intel_company.get("twitter_handle")
        or upstream_intel_company.get("twitter_url")
        or ""
    )
    # Normalise twitter handle — strip URL prefix if the field stored a full URL
    if twitter_handle.startswith("http"):
        # e.g. "https://twitter.com/algolia" → "algolia"
        twitter_handle = twitter_handle.rstrip("/").split("/")[-1]

    return str(linkedin_url), str(twitter_handle)


def _shape_post(raw: dict[str, Any], platform: str) -> dict[str, Any]:
    """Normalise a raw Apify post dict into the SocialPost field shape."""
    # LinkedIn posts use 'text' or 'description'; Twitter uses 'text' or 'full_text'
    text = (
        raw.get("text")
        or raw.get("description")
        or raw.get("full_text")
        or raw.get("content")
        or ""
    )
    date = raw.get("date") or raw.get("created_at") or raw.get("publishedAt") or None
    url = raw.get("url") or raw.get("postUrl") or raw.get("tweetUrl") or None

    return {
        "text": str(text).strip(),
        "platform": platform,
        "date": str(date) if date else None,
        "url": str(url) if url else None,
        # relevance_score and relevance_tags are set by Track 2 (LLM)
        "relevance_score": 0.0,
        "relevance_tags": [],
    }


async def _run_apify_actor(
    actor_id: str,
    input_payload: dict[str, Any],
    api_key: str,
) -> list[dict[str, Any]]:
    """Run an Apify actor and return the dataset items.

    Steps:
      1. POST /acts/{actor_id}/runs to start the run.
      2. Poll GET /acts/{actor_id}/runs/{run_id} until status is SUCCEEDED/FAILED/ABORTED.
      3. GET /datasets/{dataset_id}/items to fetch results.

    Returns empty list on any failure (non-fatal).
    """
    import asyncio

    import httpx

    headers = {"Content-Type": "application/json"}
    auth = {"token": api_key}

    actor_id_encoded = actor_id.replace("/", "~")

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Step 1: Start the actor run
        try:
            run_resp = await client.post(
                f"{_APIFY_BASE}/acts/{actor_id_encoded}/runs",
                params=auth,
                headers=headers,
                json=input_payload,
            )
            run_resp.raise_for_status()
        except Exception as exc:
            logger.warning(
                "[intel-social] Apify actor start failed",
                actor=actor_id,
                error=str(exc),
            )
            return []

        run_data = run_resp.json().get("data", {})
        run_id = run_data.get("id")
        dataset_id = run_data.get("defaultDatasetId")

        if not run_id:
            logger.warning("[intel-social] Apify run ID missing", actor=actor_id)
            return []

        # Step 2: Poll until terminal state
        deadline = asyncio.get_event_loop().time() + _RUN_TIMEOUT
        while True:
            await asyncio.sleep(_POLL_INTERVAL)
            if asyncio.get_event_loop().time() > deadline:
                logger.warning(
                    "[intel-social] Apify run timed out",
                    actor=actor_id,
                    run_id=run_id,
                )
                return []

            try:
                status_resp = await client.get(
                    f"{_APIFY_BASE}/acts/{actor_id_encoded}/runs/{run_id}",
                    params=auth,
                )
                status_resp.raise_for_status()
            except Exception as exc:
                logger.warning(
                    "[intel-social] Apify status poll failed",
                    run_id=run_id,
                    error=str(exc),
                )
                return []

            status = status_resp.json().get("data", {}).get("status", "")
            if status == "SUCCEEDED":
                break
            if status in ("FAILED", "ABORTED", "TIMED-OUT"):
                logger.warning(
                    "[intel-social] Apify run did not succeed",
                    actor=actor_id,
                    run_id=run_id,
                    status=status,
                )
                return []
            # RUNNING / READY — keep polling

        # Step 3: Fetch dataset items
        if not dataset_id:
            logger.warning("[intel-social] Apify dataset ID missing", run_id=run_id)
            return []

        try:
            items_resp = await client.get(
                f"{_APIFY_BASE}/datasets/{dataset_id}/items",
                params={**auth, "limit": _MAX_POSTS},
            )
            items_resp.raise_for_status()
            return items_resp.json() or []
        except Exception as exc:
            logger.warning(
                "[intel-social] Apify dataset fetch failed",
                dataset_id=dataset_id,
                error=str(exc),
            )
            return []


async def collect(context: ExecutionContextV2) -> dict[str, Any]:
    """Fetch LinkedIn + Twitter/X posts via Apify. Never raises.

    Returns dict with keys:
      - linkedin_posts: list of raw post dicts (shaped for SocialPost)
      - twitter_posts: list of raw post dicts (shaped for SocialPost)
      - social_sources: list of source descriptor strings

    Returns empty lists if:
      - Apify API key is not configured
      - intel-company upstream is missing
      - company_linkedin_url / twitter_handle not present in intel-company output
      - Any Apify API call fails
    """
    empty_result: dict[str, Any] = {
        "linkedin_posts": [],
        "twitter_posts": [],
        "social_sources": [],
    }

    # Guard: Apify key required
    api_key = settings.apify_api_key
    if not api_key:
        logger.info(
            "[intel-social] Apify key not configured — skipping social collection",
            domain=context.account_domain,
        )
        return empty_result

    # Guard: intel-company upstream required
    company_data: dict[str, Any] = context.upstream_results.get("intel-company", {})
    if not company_data:
        logger.info(
            "[intel-social] intel-company upstream not available — skipping social collection",
            domain=context.account_domain,
        )
        return empty_result

    linkedin_url, twitter_handle = _extract_company_social_urls(company_data)

    linkedin_posts: list[dict[str, Any]] = []
    twitter_posts: list[dict[str, Any]] = []
    sources: list[str] = []

    # ── LinkedIn scraping ───────────────────────────────────────────────────
    if linkedin_url:
        logger.info(
            "[intel-social] Fetching LinkedIn posts",
            domain=context.account_domain,
            linkedin_url=linkedin_url,
        )
        raw_li = await _run_apify_actor(
            actor_id=_LINKEDIN_ACTOR,
            input_payload={
                "companyUrl": linkedin_url,
                "maxPosts": _MAX_POSTS,
            },
            api_key=api_key,
        )
        linkedin_posts = [_shape_post(p, "linkedin") for p in raw_li if p.get("text") or p.get("description") or p.get("content")]
        if linkedin_posts:
            sources.append(f"linkedin:{linkedin_url}")
        logger.info(
            "[intel-social] LinkedIn posts collected",
            domain=context.account_domain,
            count=len(linkedin_posts),
        )
    else:
        logger.info(
            "[intel-social] No LinkedIn URL in intel-company upstream — skipping LinkedIn",
            domain=context.account_domain,
        )

    # ── Twitter/X scraping ──────────────────────────────────────────────────
    if twitter_handle:
        logger.info(
            "[intel-social] Fetching Twitter/X posts",
            domain=context.account_domain,
            twitter_handle=twitter_handle,
        )
        raw_tw = await _run_apify_actor(
            actor_id=_TWITTER_ACTOR,
            input_payload={
                "handles": [twitter_handle],
                "maxTweets": _MAX_POSTS,
                "tweetsDesiredCount": _MAX_POSTS,
            },
            api_key=api_key,
        )
        twitter_posts = [_shape_post(p, "twitter") for p in raw_tw if p.get("text") or p.get("full_text")]
        if twitter_posts:
            sources.append(f"twitter:@{twitter_handle}")
        logger.info(
            "[intel-social] Twitter/X posts collected",
            domain=context.account_domain,
            count=len(twitter_posts),
        )
    else:
        logger.info(
            "[intel-social] No Twitter handle in intel-company upstream — skipping Twitter",
            domain=context.account_domain,
        )

    return {
        "linkedin_posts": linkedin_posts,
        "twitter_posts": twitter_posts,
        "social_sources": sources,
    }
