"""PRISM Database Models -- SQLAlchemy ORM models for all tables."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# all-MiniLM-L6-v2 output dimension -- see prism_platform/pipeline/embeddings.py.
# Named once here so the ORM column and the embedding pipeline can never drift
# out of sync silently (a dimension mismatch fails loudly at insert time
# instead of at query time).
REPORT_CHUNK_EMBEDDING_DIMS = 384


class Base(DeclarativeBase):
    """Base class for all ORM models."""


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Identity (populated by intel-company)
    legal_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    company_name: Mapped[str] = mapped_column(Text, nullable=False)
    domain: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    headquarters: Mapped[str | None] = mapped_column(Text, nullable=True)
    employee_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    employee_count_source: Mapped[str | None] = mapped_column(Text, nullable=True)
    year_founded: Mapped[int | None] = mapped_column(Integer, nullable=True)
    business_model: Mapped[str | None] = mapped_column(Text, nullable=True)
    motto: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Classification
    industry: Mapped[str | None] = mapped_column(Text, nullable=True)
    sub_vertical: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)
    ticker: Mapped[str | None] = mapped_column(Text, nullable=True)
    parent_company: Mapped[str | None] = mapped_column(Text, nullable=True)
    parent_domain: Mapped[str | None] = mapped_column(Text, nullable=True)
    subsidiaries: Mapped[dict[str, Any]] = mapped_column(JSONB, default=list)
    revenue_estimate: Mapped[float | None] = mapped_column(Numeric(15, 2), nullable=True)
    revenue_source: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Social presence (populated by intel-company)
    company_linkedin_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    twitter_handle: Mapped[str | None] = mapped_column(Text, nullable=True)
    youtube_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Website snapshot
    has_search_bar: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    product_categories: Mapped[dict[str, Any]] = mapped_column(JSONB, default=list)

    # Nested entities (JSONB arrays — variable-length, always read as a unit)
    executives: Mapped[dict[str, Any]] = mapped_column(JSONB, default=list)
    competitors: Mapped[dict[str, Any]] = mapped_column(JSONB, default=list)
    recent_news: Mapped[dict[str, Any]] = mapped_column(JSONB, default=list)
    recent_blog_posts: Mapped[dict[str, Any]] = mapped_column(JSONB, default=list)

    # Field-level source citations (parsed from Perplexity inline citations)
    sources: Mapped[dict[str, Any]] = mapped_column(JSONB, default=list)

    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )


class Audit(Base):
    __tablename__ = "audits"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[str] = mapped_column(Text, nullable=False, default="system")
    status: Mapped[str] = mapped_column(Text, default="pending")
    score: Mapped[float | None] = mapped_column(Numeric(3, 2), nullable=True)
    factcheck_score: Mapped[float | None] = mapped_column(Numeric(3, 2), nullable=True)
    factcheck_action: Mapped[str | None] = mapped_column(Text, nullable=True)
    config: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    # Full audit-data JSON blob — Postgres as source of truth for the whole audit
    # (airtight plan §1.4). config stays for run-config; audit_data holds the report.
    audit_data: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    __table_args__ = (
        Index("idx_audits_account", "account_id"),
        Index("idx_audits_status", "status"),
        # ACL slice (run-2026-07-14-001, 04-spec.md §1) -- every ACL check
        # and the /acl/visible lookup filters by user_id; no index existed
        # on this column before this slice.
        Index("idx_audits_user", "user_id"),
    )


# =============================================================================
# Per-user-to-company authorization (run-2026-07-14-001, 04-spec.md §1)
# =============================================================================


class User(Base):
    """A real Clerk user -- `id` is the Clerk userId (e.g. "user_2abc...").

    `org_id` is dormant until Clerk Orgs is explicitly turned on -- never
    read by `prism_platform.auth.acl.can_user_see()` while off [C3]. See
    that module's docstring for why the column exists but is structurally
    unreferenced today.
    """

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    email: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str | None] = mapped_column(Text, nullable=True)
    org_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class AuditShare(Base):
    """An explicit `view` grant of one audit to one user (04-spec.md §1,
    §6). `permission` is locked to `'view'` only this slice -- the CHECK
    constraint below rejects anything else at the DB layer, not just in
    application code.
    """

    __tablename__ = "audit_shares"

    audit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("audits.id", ondelete="CASCADE"), primary_key=True
    )
    shared_with_user_id: Mapped[str] = mapped_column(
        Text, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    permission: Mapped[str] = mapped_column(Text, nullable=False, default="view")
    # Must equal the audit's owner; enforced at write time by the shares
    # endpoint (prism_platform/api/routers/audits.py::share_audit), not just
    # by convention.
    created_by: Mapped[str] = mapped_column(Text, ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    __table_args__ = (
        # The PK's non-leading column -- /acl/visible's core query scans by
        # this [I-3].
        Index("idx_audit_shares_shared_with", "shared_with_user_id"),
        CheckConstraint("permission = 'view'", name="ck_audit_shares_permission_view_only"),
    )


class SeenAssertion(Base):
    """`jti` replay-defense store for the signed trust-assertion channel
    (04-spec.md §4, 06-plan.md §4 design note). A table (not an in-memory
    LRU) because it survives a FastAPI process restart and is correct if
    this process is ever run with more than one uvicorn worker.
    """

    __tablename__ = "seen_assertions"

    jti: Mapped[str] = mapped_column(Text, primary_key=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ModuleExecution(Base):
    __tablename__ = "module_executions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    audit_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("audits.id", ondelete="CASCADE"), nullable=True
    )
    domain: Mapped[str] = mapped_column(Text, nullable=False, default="")
    module_name: Mapped[str] = mapped_column(Text, nullable=False)
    module_version: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, default="pending")
    wave: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    sources_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    validation_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    llm_calls: Mapped[int] = mapped_column(Integer, default=0)
    llm_cost_usd: Mapped[float] = mapped_column(Numeric(8, 4), default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint("audit_id", "module_name"),
        Index("idx_module_exec_audit", "audit_id"),
        Index("idx_module_exec_status", "audit_id", "status"),
        Index("idx_module_exec_domain_module", "domain", "module_name"),
    )


class ReportChunk(Base):
    """One retrievable chunk of an audit report, embedded for the chat agent.

    Task 5 (Track C.3) grounding store. Chunking is by report section (one
    row per top-level `Audit.audit_data` key per audit), not a fixed-token
    sliding window -- see prism_platform/pipeline/chunking.py. Retrieval is
    cosine similarity via pgvector's `<=>` operator, gated by
    prism_platform.pipeline.retrieval.SIMILARITY_THRESHOLD.
    """

    __tablename__ = "report_chunks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    audit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("audits.id", ondelete="CASCADE"), nullable=False
    )
    domain: Mapped[str] = mapped_column(Text, nullable=False)
    section_name: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(
        Vector(REPORT_CHUNK_EMBEDDING_DIMS), nullable=False
    )
    embedding_model: Mapped[str] = mapped_column(
        Text, nullable=False, default="sentence-transformers/all-MiniLM-L6-v2"
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("audit_id", "section_name", name="uq_report_chunks_audit_section"),
        Index("idx_report_chunks_audit", "audit_id"),
        Index("idx_report_chunks_domain", "domain"),
    )


class VerticalBenchmark(Base):
    __tablename__ = "vertical_benchmarks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vertical: Mapped[str] = mapped_column(Text, nullable=False)
    metric_name: Mapped[str] = mapped_column(Text, nullable=False)
    metric_value: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    sample_size: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    audit_ids: Mapped[dict[str, Any]] = mapped_column(JSONB, default=list)

    __table_args__ = (Index("idx_vertical_benchmarks_vertical", "vertical"),)


class Deliverable(Base):
    __tablename__ = "deliverables"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    audit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("audits.id", ondelete="CASCADE"), nullable=False
    )
    type: Mapped[str] = mapped_column(Text, nullable=False)
    file_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


# =============================================================================
# Algolia Customer Evidence Tables
# =============================================================================


class AlgoliaCustomer(Base):
    """Algolia customer records from the customer evidence database."""

    __tablename__ = "algolia_customers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_name: Mapped[str] = mapped_column(Text, nullable=False)
    industry: Mapped[str] = mapped_column(Text, nullable=False, default="Unknown")
    sub_vertical: Mapped[str | None] = mapped_column(Text, nullable=True)
    country: Mapped[str | None] = mapped_column(Text, nullable=True)
    website: Mapped[str | None] = mapped_column(Text, nullable=True)
    arr_range: Mapped[str | None] = mapped_column(Text, nullable=True)
    hierarchy_segment: Mapped[str | None] = mapped_column(Text, nullable=True)
    features_used: Mapped[dict[str, Any]] = mapped_column(JSONB, default=list)
    ecommerce_platform: Mapped[str | None] = mapped_column(Text, nullable=True)
    logo_rights: Mapped[bool] = mapped_column(Boolean, default=False)
    case_study_consent: Mapped[bool] = mapped_column(Boolean, default=False)
    publicity_consent: Mapped[bool] = mapped_column(Boolean, default=False)
    reference_consent: Mapped[bool] = mapped_column(Boolean, default=False)
    signed_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    go_live_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    competitor_replaced: Mapped[str | None] = mapped_column(Text, nullable=True)
    partner_ecosystem: Mapped[dict[str, Any]] = mapped_column(JSONB, default=list)
    vertical_source: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    __table_args__ = (
        Index("idx_algolia_customers_company", "company_name"),
        Index("idx_algolia_customers_industry", "industry"),
    )


class AlgoliaCaseStudy(Base):
    """Algolia case studies with URLs, features, results, and competitor takeout."""

    __tablename__ = "algolia_case_studies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_name: Mapped[str] = mapped_column(Text, nullable=False)
    url: Mapped[str | None] = mapped_column(Text, nullable=True)
    industry: Mapped[str] = mapped_column(Text, nullable=False, default="Unknown")
    sub_vertical: Mapped[str | None] = mapped_column(Text, nullable=True)
    country: Mapped[str | None] = mapped_column(Text, nullable=True)
    use_case: Mapped[str | None] = mapped_column(Text, nullable=True)
    features_used: Mapped[dict[str, Any]] = mapped_column(JSONB, default=list)
    competitor_takeout: Mapped[str | None] = mapped_column(Text, nullable=True)
    partner_integrations: Mapped[str | None] = mapped_column(Text, nullable=True)
    key_results: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(Text, default="Complete")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    __table_args__ = (
        Index("idx_algolia_case_studies_customer", "customer_name"),
        Index("idx_algolia_case_studies_industry", "industry"),
    )


class AlgoliaQuote(Base):
    """Customer quotes about Algolia from surveys, reviews, and testimonials."""

    __tablename__ = "algolia_quotes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_name: Mapped[str] = mapped_column(Text, nullable=False)
    person_name: Mapped[str] = mapped_column(Text, nullable=False)
    person_title: Mapped[str | None] = mapped_column(Text, nullable=True)
    industry: Mapped[str] = mapped_column(Text, nullable=False, default="Unknown")
    country: Mapped[str | None] = mapped_column(Text, nullable=True)
    quote_text: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    __table_args__ = (
        Index("idx_algolia_quotes_customer", "customer_name"),
        Index("idx_algolia_quotes_industry", "industry"),
    )


class AlgoliaProofpoint(Base):
    """Aggregated and customer-specific proof points with shareable metrics."""

    __tablename__ = "algolia_proofpoints"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    result_text: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str | None] = mapped_column(Text, nullable=True)
    proof_type: Mapped[str] = mapped_column(Text, nullable=False, default="Aggregated Results")
    industry: Mapped[str] = mapped_column(Text, nullable=False, default="Unknown")
    customer_or_theme: Mapped[str | None] = mapped_column(Text, nullable=True)
    shareable: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    __table_args__ = (Index("idx_algolia_proofpoints_industry", "industry"),)


class AlgoliaAdvocate(Base):
    """Customer advocates and reference volunteers willing to participate in activities."""

    __tablename__ = "algolia_advocates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    first_name: Mapped[str] = mapped_column(Text, nullable=False)
    last_name: Mapped[str] = mapped_column(Text, nullable=False)
    company_name: Mapped[str] = mapped_column(Text, nullable=False)
    job_title: Mapped[str | None] = mapped_column(Text, nullable=True)
    email: Mapped[str | None] = mapped_column(Text, nullable=True)
    industry: Mapped[str | None] = mapped_column(Text, nullable=True)
    country: Mapped[str | None] = mapped_column(Text, nullable=True)
    willing_to: Mapped[dict[str, Any]] = mapped_column(JSONB, default=list)
    person_source: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    __table_args__ = (
        Index("idx_algolia_advocates_company", "company_name"),
        Index("idx_algolia_advocates_industry", "industry"),
    )


# =============================================================================
# Algolia Knowledge Store
# =============================================================================


class AlgoliaKnowledge(Base):
    """Curated Q&A knowledge entries about Algolia — seeded or learned from conversations."""

    __tablename__ = "algolia_knowledge"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    topic: Mapped[str] = mapped_column(Text, nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    question_hash: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    sources: Mapped[dict[str, Any]] = mapped_column(JSONB, default=list)
    confidence: Mapped[float | None] = mapped_column(Numeric(3, 2), nullable=True)
    judge_score: Mapped[float | None] = mapped_column(Numeric(3, 2), nullable=True)
    # 'seed' = hand-authored baseline; 'learned' = derived from conversation gaps
    origin: Mapped[str] = mapped_column(Text, nullable=False, default="learned")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    __table_args__ = (
        Index("idx_algolia_knowledge_topic", "topic"),
        Index("idx_algolia_knowledge_origin", "origin"),
    )


class AlgoliaGap(Base):
    """Questions that could not be answered from the knowledge store — gap tracking."""

    __tablename__ = "algolia_gaps"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    question_hash: Mapped[str] = mapped_column(Text, nullable=False)
    topic: Mapped[str | None] = mapped_column(Text, nullable=True)
    conversation_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    # 'kb_miss' = no matching knowledge row; 'low_confidence' = score below threshold
    why: Mapped[str] = mapped_column(Text, nullable=False, default="kb_miss")
    status: Mapped[str] = mapped_column(Text, nullable=False, default="open")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("idx_algolia_gaps_status", "status"),
        Index("idx_algolia_gaps_question_hash", "question_hash"),
    )
