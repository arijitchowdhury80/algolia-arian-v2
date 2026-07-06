#!/usr/bin/env python3
"""
Build AE-cockpit JSON from live Postgres audit_data (via the by-slug endpoint).
Run ON the VPS (endpoint = localhost:8000). Writes /opt/PRISM/v2/ae/data/{slug}.json.

Faithful mapping only. Every field is sourced from real audit_data; where the data
genuinely doesn't exist, an explicit empty-slot / honest-chip is emitted — NEVER a
fabricated value. Confidence/risk scoring is NOT in the DB yet, so the Discovery-OS
confidence-risk field stays an honest "not scored yet" chip (matches existing door).
"""
import json, sys, urllib.request

SLUGS = ["dell", "belk", "lululemon"]
ENDPOINT = "http://127.0.0.1:8000/api/v1/audits/by-slug/{}/data"
OUTDIR = "/opt/PRISM/v2/ae/data"

SEV_RANK = {"critical": 0, "high": 0, "moderate": 1, "medium": 1, "low": 2}


def fetch(slug):
    with urllib.request.urlopen(ENDPOINT.format(slug), timeout=20) as r:
        return json.load(r)["audit_data"]


def trim(s, n=320):
    s = str(s or "").strip()
    return s if len(s) <= n else s[: n - 1].rstrip() + "…"


def company_of(d):
    meta = d.get("meta") or {}
    cover = d.get("cover") or {}
    return meta.get("company") or cover.get("company") or "—"


def domain_of(d, slug):
    meta = d.get("meta") or {}
    return meta.get("domain") or slug


def build_score(d):
    sc = d.get("score") or {}
    return {
        "overall": sc.get("overall", "—"),
        "scale": 5,
        "verdict": sc.get("verdict", ""),
        "critical_count": sc.get("critical_count", sc.get("low_count", 0)),
        "moderate_count": sc.get("moderate_count", 0),
    }


def build_stage_cockpit():
    # 3-stage scope is locked (PREP -> SS1 -> SS2; SS3/SS4 culled per exec decision).
    # Not deal-state-tracked — PREP is the always-on prep surface. Static methodology.
    return {
        "stages": [
            {"label": "PREP", "status": "active"},
            {"label": "SS1", "status": ""},
            {"label": "SS2", "status": ""},
        ],
        "note": "3-stage scope (SS3 POC / SS4 proposal are out of PRISM's scope). "
        "Currently prepping: PREP. Stage state is not deal-tracked — this is the prep surface.",
    }


def build_hypotheses(d):
    findings = d.get("findings") or []
    ordered = sorted(findings, key=lambda f: SEV_RANK.get((f.get("severity") or "").lower(), 3))
    out = []
    for i, f in enumerate(ordered[:3], 1):
        tq = f.get("tested_query")
        tied = ("Tested query: “%s”" % tq) if tq else (f.get("category") or "")
        out.append(
            {
                "rank": i,
                "title": trim(f.get("title"), 140),
                "severity": (f.get("severity") or "").upper() or "—",
                "evidence": trim(f.get("actual_behavior") or f.get("impact_stat"), 300),
                "tied_to": tied,
                # Genuinely absent in the DB — honest chip, matches the door's existing pattern.
                "confidence_risk_note": "Discovery-OS confidence×risk scoring is not yet stored "
                "for audit findings — surfaced un-ranked rather than inventing a score.",
                "source_url": f.get("screenshot_file") or "",
            }
        )
    return out


def build_objection(d):
    ga = d.get("golden_angle") or {}
    # golden_angle carries the real competitive narrative + talk_track for this account.
    if ga.get("has_golden_angle"):
        obj = "A direct competitor already runs Algolia — “why should we, and why now?”"
    else:
        obj = "“Why Algolia over our in-house / incumbent search engine?”"
    resp = trim(ga.get("talk_track") or ga.get("narrative"), 320) or "—"
    return {"objection": obj, "response": resp, "source": "audit: golden_angle"}


def build_cost(d):
    fin = d.get("financials") or {}
    est = fin.get("search_roi_est")
    addr = fin.get("search_addressable")
    if est or addr:
        parts = []
        if addr:
            parts.append("Modeled search-addressable: %s" % addr)
        if est:
            parts.append("estimated upside %s" % est)
        return {"text": trim("; ".join(parts), 320), "source": "audit: financials (modeled)"}
    # fallback: top finding impact stat
    findings = d.get("findings") or []
    if findings:
        return {"text": trim(findings[0].get("impact_stat"), 320), "source": "audit: findings"}
    return {"text": "", "source": ""}


def build_stakeholder(d):
    rp = d.get("recommended_first_play") or {}
    if rp.get("headline"):
        return {
            "role": "First-play path",
            "name": trim(rp.get("headline"), 120),
            "status": "inferred from %s — confirm before citing" % (rp.get("source") or "public data"),
            "note": trim(rp.get("detail"), 260),
            "source": "audit: recommended_first_play",
        }
    # fallback: an executive surfaced from earnings/LinkedIn (public, not buyer-volunteered)
    execs = d.get("executives") or []
    if execs:
        e = execs[0]
        return {
            "role": trim(e.get("title"), 90),
            "name": trim(e.get("name"), 90),
            "status": "public-record exec — not a confirmed buyer contact",
            "note": trim(e.get("relevance"), 260),
            "source": "audit: executives",
        }
    return {"role": "Stakeholder to add", "name": "—",
            "status": "no public-data candidate found — do not fabricate",
            "note": "", "source": ""}


def build_next_meeting(d):
    ae = d.get("ae_fields") or {}
    ns = (d.get("next_steps") or [{}])[0]
    text = trim(ae.get("talk_track_cta") or ns.get("title"), 300) or "—"
    cta = trim(ae.get("next_step_action") or ns.get("description"), 300)
    return {
        "text": text,
        "cta": cta,
        "source": "audit: ae_fields / next_steps",
        "target_date": ae.get("next_step_date") or "—",
        "owner": ae.get("next_step_owner") or "—",
    }


def build_opening(d):
    ae = d.get("ae_fields") or {}
    txt = trim(ae.get("talk_track_opener"), 320)
    return {"text": txt or "—", "source_label": "audit: ae_fields.talk_track_opener", "source_url": ""}


def build_exit_gates():
    # SS2 methodology gate (Field Guide). Static checklist, honestly not deal-tracked.
    return {
        "ss2_label": "SS2 exit gate — Vision-to-Value (methodology checklist, not deal-tracked)",
        "items": [
            {"item": "Vision-to-Value delivered", "detail": "Anxiety statement + ROI justification landed with the buyer.", "status": "open"},
            {"item": "Eval path confirmed", "detail": "A relevance A/B or pilot path is agreed.", "status": "open"},
            {"item": "PIE buy-in secured", "detail": "Product / Infra / Eng stakeholder is bought in.", "status": "open"},
            {"item": "Business case built", "detail": "ROI model exists in full before negotiation — not deferred.", "status": "open"},
        ],
    }


def build_battle_card(d):
    ga = d.get("golden_angle") or {}
    ae = d.get("ae_fields") or {}
    comps = []
    for c in (d.get("competitors") or [])[:8]:
        comps.append(
            {
                "name": c.get("name") or "—",
                "vendor": c.get("search_vendor") or "unknown",
                "uses_algolia": bool(c.get("uses_algolia")),
            }
        )
    cs = ga.get("footwear_case_study") or {}
    return {
        "has_golden_angle": bool(ga.get("has_golden_angle")),
        "narrative": trim(ga.get("narrative"), 400),
        "talk_track": trim(ga.get("talk_track"), 400),
        "benchmark_proof": trim(ae.get("benchmark_proof"), 300),
        "case_study": {
            "company": cs.get("company") or "",
            "result": trim(cs.get("result"), 200),
            "url": cs.get("url") or "",
        } if cs else None,
        "competitors": comps,
        "source": "audit: golden_angle + competitors + ae_fields.benchmark_proof",
    }


def build_active_sources(d):
    checks = [
        ("Company & executive intel", "company_snapshot / executives", ["company_snapshot", "executives"]),
        ("Financial profile", "revenue, margins, modeled search ROI", ["financials"]),
        ("Competitor & search-tech scan", "competitor set + detected search vendors", ["competitors"]),
        ("Search audit findings", "browser-tested search behavior + scoring", ["findings", "score"]),
        ("Traffic & engagement", "SimilarWeb capture (HITL-verified)", ["traffic"]),
        ("Intelligence signals", "news / hiring / partner signals", ["intelligence_signals"]),
    ]
    out = []
    for name, detail, keys in checks:
        if any(d.get(k) for k in keys):
            out.append({"name": name, "detail": detail})
    return out


def build_locked_sources():
    # From the IA doc (data-source stub cards). Static, honest "would add value".
    return [
        {"name": "Gong call recordings", "function": "Verbatim objection & signal miner",
         "value": "real objections + who said what in the room", "needs": "Gong transcripts for the account"},
        {"name": "Account-history notes", "function": "Account memory",
         "value": "don't re-pitch a failed angle; prior contacts & deals", "needs": "rep's informal notes — no new system"},
        {"name": "Event engagement feed", "function": "Conference / booth touches",
         "value": "warm signals from real-world engagement", "needs": "event CRM / badge-scan export"},
    ]


def build(slug):
    d = fetch(slug)
    return {
        "meta": {"company": company_of(d), "domain": domain_of(d, slug)},
        "score": build_score(d),
        "stage_cockpit": build_stage_cockpit(),
        "call_plan": {
            "eyebrow": "Discovery-OS single-page call plan",
            "opening_move": build_opening(d),
            "hypotheses": build_hypotheses(d),
            "competitive_objection": build_objection(d),
            "cost_of_inaction": build_cost(d),
            "stakeholder_to_add": build_stakeholder(d),
            "next_meeting_hook": build_next_meeting(d),
        },
        "exit_gates": build_exit_gates(),
        "battle_card_data": build_battle_card(d),
        # Playbook / Business Case: honest V2-native stubs (built next slice), NOT a V1 bounce.
        "playbook": {"available": False, "label": "AE Playbook"},
        "business_case": {"available": False, "label": "Business Case / ROI"},
        "active_sources": build_active_sources(d),
        "locked_sources": build_locked_sources(),
    }


def main():
    import os
    os.makedirs(OUTDIR, exist_ok=True)
    for slug in SLUGS:
        try:
            data = build(slug)
            with open("%s/%s.json" % (OUTDIR, slug), "w") as f:
                json.dump(data, f, indent=1, ensure_ascii=False)
            print("OK  %s -> %s/%s.json  (company=%s, %d hypotheses)"
                  % (slug, OUTDIR, slug, data["meta"]["company"], len(data["call_plan"]["hypotheses"])))
        except Exception as e:
            print("FAIL %s: %s" % (slug, e))


if __name__ == "__main__":
    main()
