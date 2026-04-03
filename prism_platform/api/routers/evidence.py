"""PRISM Evidence Router — query Algolia customer evidence for prospect matching."""

from __future__ import annotations

from typing import Any, Optional

import structlog
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import or_, select

from prism_platform.api.deps import DbSession
from prism_platform.core.domain_normalizer import normalize_domain
from prism_platform.db.models import (
    AlgoliaAdvocate,
    AlgoliaCaseStudy,
    AlgoliaCustomer,
    AlgoliaProofpoint,
    AlgoliaQuote,
    ModuleExecution,
)

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class CustomerResponse(BaseModel):
    """Public-safe customer record (only logo_rights or publicity_consent customers)."""

    model_config = ConfigDict(from_attributes=True)

    company_name: str
    industry: str
    features_used: list[Any]
    ecommerce_platform: str | None = None
    case_study_available: bool = False


class CaseStudyResponse(BaseModel):
    """Case study summary for evidence matching."""

    model_config = ConfigDict(from_attributes=True)

    customer_name: str
    url: str | None = None
    industry: str
    use_case: str | None = None
    features_used: list[Any]
    key_results: str | None = None
    competitor_takeout: str | None = None
    status: str


class QuoteResponse(BaseModel):
    """Customer quote for evidence matching."""

    model_config = ConfigDict(from_attributes=True)

    customer_name: str
    person_name: str
    person_title: str | None = None
    quote_text: str
    source: str | None = None


class ProofpointResponse(BaseModel):
    """Shareable proofpoint for evidence matching."""

    model_config = ConfigDict(from_attributes=True)

    result_text: str
    source: str | None = None
    proof_type: str
    customer_or_theme: str | None = None


class AdvocateResponse(BaseModel):
    """Customer advocate summary."""

    model_config = ConfigDict(from_attributes=True)

    first_name: str
    last_name: str
    company_name: str
    job_title: str | None = None
    industry: str | None = None
    country: str | None = None
    willing_to: list[Any]


class CompetitorCustomerHit(BaseModel):
    """A prospect competitor that is also an Algolia customer."""

    model_config = ConfigDict(extra="forbid")

    competitor_name: str
    algolia_customer: str


class EvidenceMatchResponse(BaseModel):
    """Compiled evidence package for a prospect domain."""

    model_config = ConfigDict(extra="forbid")

    domain: str
    prospect_industry: str | None = None
    matched_customers: list[CustomerResponse]
    matched_case_studies: list[CaseStudyResponse]
    matched_quotes: list[QuoteResponse]
    matched_proofpoints: list[ProofpointResponse]
    competitor_is_customer: bool = False
    competitor_customers: list[CompetitorCustomerHit]
    available_advocates: list[AdvocateResponse]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/customers", response_model=list[CustomerResponse])
async def list_customers(
    session: DbSession,
    industry: Optional[str] = Query(default=None, description="Filter by industry (case-insensitive)"),
    vertical: Optional[str] = Query(default=None, description="Filter by sub_vertical (case-insensitive)"),
    partner: Optional[str] = Query(default=None, description="Filter by partner ecosystem (e.g. 'Adobe')"),
    feature: Optional[str] = Query(default=None, description="Filter by feature used (e.g. 'Neural Search')"),
    arr_tier: Optional[str] = Query(default=None, description="Filter by ARR tier (e.g. 'Enterprise 100k+')"),
) -> list[CustomerResponse]:
    """List customers with logo_rights or publicity_consent, optionally filtered."""
    logger.info(
        "evidence.list_customers.start",
        industry=industry, vertical=vertical, partner=partner, feature=feature, arr_tier=arr_tier,
    )
    try:
        stmt = select(AlgoliaCustomer).where(
            or_(
                AlgoliaCustomer.logo_rights.is_(True),
                AlgoliaCustomer.publicity_consent.is_(True),
            )
        )
        if industry:
            stmt = stmt.where(AlgoliaCustomer.industry.ilike(f"%{industry}%"))
        if vertical:
            stmt = stmt.where(AlgoliaCustomer.sub_vertical.ilike(f"%{vertical}%"))
        if partner:
            # Query JSONB array for partner name (e.g. partner_ecosystem @> '"Adobe"')
            stmt = stmt.where(AlgoliaCustomer.partner_ecosystem.op("@>")(f'"{partner}"'))
        if feature:
            # Query JSONB array for feature name
            stmt = stmt.where(AlgoliaCustomer.features_used.op("@>")(f'"{feature}"'))
        if arr_tier:
            stmt = stmt.where(AlgoliaCustomer.arr_range.ilike(f"%{arr_tier}%"))

        result = await session.execute(stmt.order_by(AlgoliaCustomer.company_name))
        customers = result.scalars().all()

        responses = [
            CustomerResponse(
                company_name=c.company_name,
                industry=c.industry,
                features_used=c.features_used if c.features_used else [],
                ecommerce_platform=c.ecommerce_platform,
                case_study_available=bool(c.case_study_consent),
            )
            for c in customers
        ]
        logger.info("evidence.list_customers.done", count=len(responses))
        return responses

    except Exception as exc:
        logger.error("evidence.list_customers.failed", error=str(exc))
        raise HTTPException(status_code=500, detail="Failed to list customers.") from exc


@router.get("/case-studies", response_model=list[CaseStudyResponse])
async def list_case_studies(
    session: DbSession,
    industry: Optional[str] = Query(default=None, description="Filter by industry (case-insensitive)"),
    customer: Optional[str] = Query(default=None, description="Filter by customer name (case-insensitive)"),
) -> list[CaseStudyResponse]:
    """List case studies, optionally filtered by industry or customer."""
    logger.info("evidence.list_case_studies.start", industry=industry, customer=customer)
    try:
        stmt = select(AlgoliaCaseStudy)
        if industry:
            stmt = stmt.where(AlgoliaCaseStudy.industry.ilike(f"%{industry}%"))
        if customer:
            stmt = stmt.where(AlgoliaCaseStudy.customer_name.ilike(f"%{customer}%"))

        result = await session.execute(stmt.order_by(AlgoliaCaseStudy.customer_name))
        rows = result.scalars().all()

        responses = [
            CaseStudyResponse(
                customer_name=r.customer_name,
                url=r.url,
                industry=r.industry,
                use_case=r.use_case,
                features_used=r.features_used if r.features_used else [],
                key_results=r.key_results,
                competitor_takeout=r.competitor_takeout,
                status=r.status,
            )
            for r in rows
        ]
        logger.info("evidence.list_case_studies.done", count=len(responses))
        return responses

    except Exception as exc:
        logger.error("evidence.list_case_studies.failed", error=str(exc))
        raise HTTPException(status_code=500, detail="Failed to list case studies.") from exc


@router.get("/quotes", response_model=list[QuoteResponse])
async def list_quotes(
    session: DbSession,
    industry: Optional[str] = Query(default=None, description="Filter by industry (case-insensitive)"),
    feature: Optional[str] = Query(default=None, description="Text search on quote_text for a feature keyword"),
) -> list[QuoteResponse]:
    """List quotes, optionally filtered by industry or feature keyword."""
    logger.info("evidence.list_quotes.start", industry=industry, feature=feature)
    try:
        stmt = select(AlgoliaQuote)
        if industry:
            stmt = stmt.where(AlgoliaQuote.industry.ilike(f"%{industry}%"))
        if feature:
            stmt = stmt.where(AlgoliaQuote.quote_text.ilike(f"%{feature}%"))

        result = await session.execute(stmt.order_by(AlgoliaQuote.customer_name))
        rows = result.scalars().all()

        responses = [
            QuoteResponse(
                customer_name=r.customer_name,
                person_name=r.person_name,
                person_title=r.person_title,
                quote_text=r.quote_text,
                source=r.source,
            )
            for r in rows
        ]
        logger.info("evidence.list_quotes.done", count=len(responses))
        return responses

    except Exception as exc:
        logger.error("evidence.list_quotes.failed", error=str(exc))
        raise HTTPException(status_code=500, detail="Failed to list quotes.") from exc


@router.get("/proofpoints", response_model=list[ProofpointResponse])
async def list_proofpoints(
    session: DbSession,
    industry: Optional[str] = Query(default=None, description="Filter by industry (case-insensitive)"),
) -> list[ProofpointResponse]:
    """List shareable proofpoints, optionally filtered by industry."""
    logger.info("evidence.list_proofpoints.start", industry=industry)
    try:
        stmt = select(AlgoliaProofpoint).where(AlgoliaProofpoint.shareable.is_(True))
        if industry:
            stmt = stmt.where(AlgoliaProofpoint.industry.ilike(f"%{industry}%"))

        result = await session.execute(stmt.order_by(AlgoliaProofpoint.customer_or_theme))
        rows = result.scalars().all()

        responses = [
            ProofpointResponse(
                result_text=r.result_text,
                source=r.source,
                proof_type=r.proof_type,
                customer_or_theme=r.customer_or_theme,
            )
            for r in rows
        ]
        logger.info("evidence.list_proofpoints.done", count=len(responses))
        return responses

    except Exception as exc:
        logger.error("evidence.list_proofpoints.failed", error=str(exc))
        raise HTTPException(status_code=500, detail="Failed to list proofpoints.") from exc


@router.get("/advocates", response_model=list[AdvocateResponse])
async def list_advocates(
    session: DbSession,
    industry: Optional[str] = Query(default=None, description="Filter by industry (case-insensitive)"),
    company: Optional[str] = Query(default=None, description="Filter by company name (case-insensitive)"),
) -> list[AdvocateResponse]:
    """List customer advocates, optionally filtered by industry or company."""
    logger.info("evidence.list_advocates.start", industry=industry, company=company)
    try:
        stmt = select(AlgoliaAdvocate)
        if industry:
            stmt = stmt.where(AlgoliaAdvocate.industry.ilike(f"%{industry}%"))
        if company:
            stmt = stmt.where(AlgoliaAdvocate.company_name.ilike(f"%{company}%"))

        result = await session.execute(stmt.order_by(AlgoliaAdvocate.company_name))
        rows = result.scalars().all()

        responses = [
            AdvocateResponse(
                first_name=r.first_name,
                last_name=r.last_name,
                company_name=r.company_name,
                job_title=r.job_title,
                industry=r.industry,
                country=r.country,
                willing_to=r.willing_to if r.willing_to else [],
            )
            for r in rows
        ]
        logger.info("evidence.list_advocates.done", count=len(responses))
        return responses

    except Exception as exc:
        logger.error("evidence.list_advocates.failed", error=str(exc))
        raise HTTPException(status_code=500, detail="Failed to list advocates.") from exc


@router.get("/match", response_model=EvidenceMatchResponse)
async def match_evidence(
    session: DbSession,
    domain: Optional[str] = Query(default=None, description="Prospect domain to match evidence against"),
) -> EvidenceMatchResponse:
    """Match Algolia customer evidence against a prospect domain's intel data.

    Reads the prospect's intel-company module output to extract industry and
    competitor information, then queries all evidence tables for matches.
    """
    if not domain:
        raise HTTPException(status_code=400, detail="domain query parameter is required.")

    domain = normalize_domain(domain)
    logger.info("evidence.match.start", domain=domain)
    try:
        # Step 1: Read prospect intel-company output
        intel_stmt = (
            select(ModuleExecution)
            .where(
                ModuleExecution.domain == domain,
                ModuleExecution.module_name == "intel-company",
                ModuleExecution.status == "success",
            )
            .order_by(ModuleExecution.completed_at.desc())
            .limit(1)
        )
        intel_result = await session.execute(intel_stmt)
        intel_row = intel_result.scalar_one_or_none()

        prospect_industry: str | None = None
        competitor_domains: list[str] = []
        competitor_names: list[str] = []

        if intel_row and intel_row.output_json:
            output = intel_row.output_json
            prospect_industry = output.get("industry") or output.get("vertical")
            # Extract competitors — support both list-of-dicts and list-of-strings
            raw_competitors = output.get("competitors", [])
            for comp in raw_competitors:
                if isinstance(comp, dict):
                    if comp.get("domain"):
                        competitor_domains.append(comp["domain"].lower().strip())
                    if comp.get("name"):
                        competitor_names.append(comp["name"])
                elif isinstance(comp, str):
                    competitor_names.append(comp)

            logger.info(
                "evidence.match.intel_loaded",
                domain=domain,
                prospect_industry=prospect_industry,
                competitor_count=len(competitor_names),
            )
        else:
            logger.warning("evidence.match.no_intel", domain=domain)

        # Step 2: Query customers (privacy-gated)
        cust_stmt = select(AlgoliaCustomer).where(
            or_(
                AlgoliaCustomer.logo_rights.is_(True),
                AlgoliaCustomer.publicity_consent.is_(True),
            )
        )
        if prospect_industry:
            cust_stmt = cust_stmt.where(AlgoliaCustomer.industry.ilike(f"%{prospect_industry}%"))

        cust_result = await session.execute(cust_stmt.order_by(AlgoliaCustomer.company_name))
        customers = cust_result.scalars().all()

        matched_customers = [
            CustomerResponse(
                company_name=c.company_name,
                industry=c.industry,
                features_used=c.features_used if c.features_used else [],
                ecommerce_platform=c.ecommerce_platform,
                case_study_available=bool(c.case_study_consent),
            )
            for c in customers
        ]

        # Step 3: Query case studies
        cs_stmt = select(AlgoliaCaseStudy)
        if prospect_industry:
            cs_stmt = cs_stmt.where(AlgoliaCaseStudy.industry.ilike(f"%{prospect_industry}%"))

        cs_result = await session.execute(cs_stmt.order_by(AlgoliaCaseStudy.customer_name))
        case_studies = cs_result.scalars().all()

        matched_case_studies = [
            CaseStudyResponse(
                customer_name=r.customer_name,
                url=r.url,
                industry=r.industry,
                use_case=r.use_case,
                features_used=r.features_used if r.features_used else [],
                key_results=r.key_results,
                competitor_takeout=r.competitor_takeout,
                status=r.status,
            )
            for r in case_studies
        ]

        # Step 4: Query quotes
        q_stmt = select(AlgoliaQuote)
        if prospect_industry:
            q_stmt = q_stmt.where(AlgoliaQuote.industry.ilike(f"%{prospect_industry}%"))

        q_result = await session.execute(q_stmt.order_by(AlgoliaQuote.customer_name))
        quotes = q_result.scalars().all()

        matched_quotes = [
            QuoteResponse(
                customer_name=r.customer_name,
                person_name=r.person_name,
                person_title=r.person_title,
                quote_text=r.quote_text,
                source=r.source,
            )
            for r in quotes
        ]

        # Step 5: Query proofpoints (shareable only)
        pp_stmt = select(AlgoliaProofpoint).where(AlgoliaProofpoint.shareable.is_(True))
        if prospect_industry:
            pp_stmt = pp_stmt.where(AlgoliaProofpoint.industry.ilike(f"%{prospect_industry}%"))

        pp_result = await session.execute(pp_stmt.order_by(AlgoliaProofpoint.customer_or_theme))
        proofpoints = pp_result.scalars().all()

        matched_proofpoints = [
            ProofpointResponse(
                result_text=r.result_text,
                source=r.source,
                proof_type=r.proof_type,
                customer_or_theme=r.customer_or_theme,
            )
            for r in proofpoints
        ]

        # Step 6: Check competitor-is-customer (Golden Angle)
        competitor_customer_hits: list[CompetitorCustomerHit] = []
        if competitor_domains or competitor_names:
            all_cust_result = await session.execute(select(AlgoliaCustomer))
            all_customers = all_cust_result.scalars().all()

            for ac in all_customers:
                # Match by website domain
                ac_website = (ac.website or "").lower().strip()
                for cd in competitor_domains:
                    if cd and ac_website and (cd in ac_website or ac_website in cd):
                        competitor_customer_hits.append(
                            CompetitorCustomerHit(
                                competitor_name=cd,
                                algolia_customer=ac.company_name,
                            )
                        )
                        break
                else:
                    # Match by company name
                    ac_name_lower = ac.company_name.lower()
                    for cn in competitor_names:
                        if cn.lower() in ac_name_lower or ac_name_lower in cn.lower():
                            competitor_customer_hits.append(
                                CompetitorCustomerHit(
                                    competitor_name=cn,
                                    algolia_customer=ac.company_name,
                                )
                            )
                            break

        # Step 7: Query advocates
        adv_stmt = select(AlgoliaAdvocate)
        if prospect_industry:
            adv_stmt = adv_stmt.where(AlgoliaAdvocate.industry.ilike(f"%{prospect_industry}%"))

        adv_result = await session.execute(adv_stmt.order_by(AlgoliaAdvocate.company_name))
        advocates = adv_result.scalars().all()

        available_advocates = [
            AdvocateResponse(
                first_name=r.first_name,
                last_name=r.last_name,
                company_name=r.company_name,
                job_title=r.job_title,
                industry=r.industry,
                country=r.country,
                willing_to=r.willing_to if r.willing_to else [],
            )
            for r in advocates
        ]

        response = EvidenceMatchResponse(
            domain=domain,
            prospect_industry=prospect_industry,
            matched_customers=matched_customers,
            matched_case_studies=matched_case_studies,
            matched_quotes=matched_quotes,
            matched_proofpoints=matched_proofpoints,
            competitor_is_customer=len(competitor_customer_hits) > 0,
            competitor_customers=competitor_customer_hits,
            available_advocates=available_advocates,
        )

        logger.info(
            "evidence.match.done",
            domain=domain,
            prospect_industry=prospect_industry,
            customers=len(matched_customers),
            case_studies=len(matched_case_studies),
            quotes=len(matched_quotes),
            proofpoints=len(matched_proofpoints),
            competitor_hits=len(competitor_customer_hits),
            advocates=len(available_advocates),
        )
        return response

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("evidence.match.failed", domain=domain, error=str(exc))
        raise HTTPException(status_code=500, detail="Failed to match evidence.") from exc
