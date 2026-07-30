"""audit_data_schema.py — Pydantic v2 models for audit-data.json (the SPA data contract).

VENDORED VERBATIM from the canonical Algolia Search Audit skill:
  ~/.claude/skills/algolia-search-audit/scripts/audit_data_schema.py

This is the single source of truth for what the SPA + deliverable HTML templates read.
PRISM's `audit-report` module produces an `AuditData` and the (vendored) renderer turns it
into the SPA + deliverables. Keep this in sync with the skill; do not diverge field names —
the templates hardcode them and wrong keys render blank.

Pydantic enforces: required fields present, citations where the template renders them,
channel-specific rules (video_script for video), placeholder/source-note blocking, canonical
score keys.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

# ── ABX Campaign ──────────────────────────────────────────────────────────────

class ABXContact(BaseModel):
    name: str
    id: str  # snake_case slug — required for SPA contactMap lookup
    title: str | None = None
    role: str | None = None
    company: str | None = None
    linkedin_url: str | None = None

    model_config = {"extra": "allow"}


class ABXTouch(BaseModel):
    touch: int
    day: str
    channel: Literal["email", "linkedin", "video"]
    target: str = "all"
    subject: str | None = None
    body: str  # Email: full copy. LinkedIn: clean message. Video: short delivery email.
    message: str | None = None  # Preview only — NOT rendered in SPA for email/video

    # Video-specific (required when channel == "video")
    video_script: str | None = None
    video_platform: str | None = "Loom"
    video_duration_target: str | None = None
    email_subject: str | None = None
    email_body: str | None = None

    @model_validator(mode="after")
    def validate_channel_rules(self) -> ABXTouch:
        body = self.body or ""
        channel = self.channel

        placeholder_markers = [
            "Pending —", "Pending—", "TBD", "[PLACEHOLDER]",
            "will be generated", "not yet complete",
        ]
        for marker in placeholder_markers:
            if marker.lower() in body.lower():
                raise ValueError(
                    f"Touch {self.touch} ({channel}): body contains placeholder text '{marker}'. "
                    f"ABX campaign must be fully generated before JSON update."
                )

        if "**Source notes:**" in body or "Source notes:" in body:
            raise ValueError(
                f"Touch {self.touch} ({channel}): body contains 'Source notes:' — "
                f"source notes are internal AE prep and must NOT appear in email body. "
                f"Extract only the sendable copy between **Body:** and **Source notes:**."
            )

        if len(body.strip()) < 50:
            raise ValueError(
                f"Touch {self.touch} ({channel}): body is {len(body.strip())} chars — too short. "
                f"Minimum 50 chars required. Likely a placeholder or extraction failure."
            )

        if channel == "video":
            if not self.video_script:
                raise ValueError(
                    f"Touch {self.touch} (video): video_script is required for video touches. "
                    f"The SPA template reads t.video_script to render the Loom script panel. "
                    f"Do NOT put the script in t.body — that field holds the short delivery email."
                )
            script = self.video_script or ""
            if len(script.strip()) < 100:
                raise ValueError(
                    f"Touch {self.touch} (video): video_script is {len(script.strip())} chars — "
                    f"too short for a 2-minute script. Loom script should be 200-280 words."
                )

        return self


class ABXSequence(BaseModel):
    touches: list[ABXTouch]
    contacts: list[ABXContact]
    total_touches: int = Field(default=9)
    duration_days: int = Field(default=21)
    channels: list[str] = Field(default_factory=lambda: ["Email", "LinkedIn", "Video"])

    @model_validator(mode="after")
    def validate_sequence(self) -> ABXSequence:
        if len(self.touches) < 3:
            raise ValueError(
                f"abx_sequence.touches has {len(self.touches)} touches — minimum 3 required. "
                f"Run algolia-campaign-abx skill to generate the full campaign."
            )
        if len(self.contacts) < 1:
            raise ValueError(
                "abx_sequence.contacts is empty — must have at least 1 contact with id field."
            )
        for c in self.contacts:
            if not c.id:
                raise ValueError(
                    f"Contact '{c.name}' missing id field. "
                    f"id must be snake_case slug e.g. 'henning_kruger'."
                )
        return self


# ── ICP Mapping ───────────────────────────────────────────────────────────────

class ICPPriorityToProduct(BaseModel):
    pain: str  # canonical — Solution Map reads p.pain
    their_priority: str | None = None  # alias — Discovery Q card reads p.their_priority
    evidence: str | None = None  # exec quote that justifies the Q
    exact_quote: str | None = None  # alias for evidence
    product: str  # canonical — Solution Map reads p.product
    algolia_solution: str | None = None  # alias — Discovery Q card reads p.algolia_solution
    discovery_question: str | None = None
    proof_company: str | None = None
    proof_url: str | None = None
    proof_result: str | None = None

    @model_validator(mode="after")
    def validate_citations_and_aliases(self) -> ICPPriorityToProduct:
        if not self.their_priority:
            self.their_priority = self.pain
        if not self.algolia_solution:
            self.algolia_solution = self.product

        if self.discovery_question:
            has_evidence = bool(self.evidence or self.exact_quote)
            if not has_evidence:
                raise ValueError(
                    f"Q card for '{self.pain[:40]}...' has discovery_question but no "
                    f"evidence/exact_quote. Add the supporting exec quote."
                )

        if self.proof_company and not self.proof_url:
            raise ValueError(
                f"proof_company='{self.proof_company}' set but proof_url is missing. "
                f"Every case study reference must link to a verifiable source."
            )

        return self


class ICPMapping(BaseModel):
    priority_to_product: list[ICPPriorityToProduct] = Field(default_factory=list)


# ── Executives ────────────────────────────────────────────────────────────────

class Executive(BaseModel):
    name: str
    title: str
    quote: str
    quote_context: str | None = None
    source: str | None = None
    source_url: str | None = None  # alias used in some places
    quote_source: str | None = None  # canonical field template reads

    @model_validator(mode="after")
    def validate_quote_citation(self) -> Executive:
        has_citation = bool(self.quote_source or self.source_url or self.source)
        if not has_citation:
            raise ValueError(
                f"Executive '{self.name}': quote has no citation. "
                f"Set quote_source (preferred), source_url, or source."
            )
        if not self.quote_source and self.source_url:
            self.quote_source = self.source_url
        return self


# ── Intelligence Signals ──────────────────────────────────────────────────────

VALID_SIGNAL_TYPES = {
    "earnings_quote", "media_quote", "sec_risk", "hiring_signal",
    "social_signal", "news_signal",
}

VALID_SIGNAL_TYPES_EXTENDED = VALID_SIGNAL_TYPES | {
    "exec", "news", "hiring", "social", "partner", "industry",
    "industry-risk", "industry-opp", "funding", "digital_transformation",
    "competitor", "leadership", "expansion", "regulatory",
}


class IntelligenceSignal(BaseModel):
    type: str
    title: str | None = None
    signal: str | None = None
    badge_label: str | None = None
    detail: str | None = None
    relevance: str | None = None
    source_url: str | None = None
    source_date: str | None = None
    urgency_score: int | None = None
    ae_action: str | None = None

    model_config = {"extra": "allow"}

    @model_validator(mode="after")
    def validate_signal(self) -> IntelligenceSignal:
        all_valid = VALID_SIGNAL_TYPES_EXTENDED
        if self.type not in all_valid:
            raise ValueError(
                f"intelligence_signals: type='{self.type}' is not recognised. "
                f"Valid types: {', '.join(sorted(all_valid))}"
            )
        has_content = bool(self.title or self.signal or self.badge_label or self.detail)
        if not has_content:
            raise ValueError(
                f"intelligence_signals[type={self.type}]: no content field found. "
                f"Must have at least one of: title, signal, badge_label, detail."
            )
        detail = self.detail or self.signal or ""
        if len(detail) > 50 and not self.source_url:
            raise ValueError(
                f"Signal '{(self.title or self.signal or '')[:40]}' has content "
                f"but no source_url. Every signal claim must be verifiable."
            )
        return self


# ── Finding Card Enrichment Models ────────────────────────────────────────────

class AnxietyDriver(BaseModel):
    calculation: str
    competitor_comparison: str
    quantified_impact: str

    @field_validator("quantified_impact")
    @classmethod
    def impact_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("quantified_impact cannot be empty")
        return v


class IndustryBenchmark(BaseModel):
    metric_name: str
    best_in_class: str
    current_score: str
    gap: str
    source: str

    @field_validator("source")
    @classmethod
    def source_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("source is required for IndustryBenchmark")
        return v


class DiscoveryQuestions(BaseModel):
    situation: str
    problem: str
    implication: str
    need_payoff: str


class AlgoliaAngle(BaseModel):
    capability: str
    specifics: str
    time_to_value: str | None = None


class ValueMap(BaseModel):
    gap: str
    capability: str
    outcome: str
    metric: str


class ObjectionHandler(BaseModel):
    objection: str
    counter: str
    evidence_ref: str | None = None


# ── Findings (Browser Audit) ──────────────────────────────────────────────────

class Finding(BaseModel):
    id: str
    title: str
    severity: Literal["critical", "moderate", "positive"]
    category: str
    tested_query: str
    actual_behavior: str
    algolia_solution: str | None = None
    algolia_case_study_company: str | None = None
    algolia_case_study_url: str | None = None
    algolia_case_study_result: str | None = None
    screenshot_file: str | None = None
    expected_behavior: str | None = None
    impact_stat: str | None = None
    impact_stat_source: str | None = None

    pain_frame: str | None = None
    anxiety_driver: AnxietyDriver | None = None
    industry_benchmark: IndustryBenchmark | None = None
    discovery_questions: DiscoveryQuestions | None = None
    algolia_angle: AlgoliaAngle | None = None
    value_map: ValueMap | None = None
    objection_handling: list[ObjectionHandler] = Field(default_factory=list)
    model_config = {"extra": "allow"}

    @model_validator(mode="after")
    def validate_finding(self) -> Finding:
        if self.algolia_case_study_company and not self.algolia_case_study_url:
            raise ValueError(
                f"Finding '{self.id}': algolia_case_study_company="
                f"'{self.algolia_case_study_company}' set but no algolia_case_study_url."
            )
        if self.impact_stat and not self.impact_stat_source:
            raise ValueError(
                f"Finding '{self.id}': impact_stat set but no impact_stat_source. "
                f"Impact stats with no source URL are BLOCKING — remove or cite."
            )
        return self


# ── Strategic Angles ──────────────────────────────────────────────────────────

class StrategicAngle(BaseModel):
    label: str
    hook: str
    pain_points: list[str]
    discovery_question: str | None = None
    algolia_proof: str | None = None
    objection: str | None = None
    objection_counter: str | None = None
    source: str | None = None
    urgency: str | None = None

    @model_validator(mode="after")
    def validate_angle(self) -> StrategicAngle:
        if not self.source:
            raise ValueError(
                f"strategic_angles['{self.label}']: source is required. "
                f"Every angle must cite the trigger signal that justifies it."
            )
        if not self.algolia_proof:
            raise ValueError(
                f"strategic_angles['{self.label}']: algolia_proof is required. "
                f"Every angle must reference a verified Algolia case study metric."
            )
        return self


# ── Score ─────────────────────────────────────────────────────────────────────

CANONICAL_SCORE_KEYS = {
    "latency", "typo_tolerance", "query_suggestions_empty_state",
    "intent_detection", "merchandising_consistency", "content_commerce_ux",
    "semantic_nlp_search", "dynamic_facets_personalization",
    "recommendations_merchandising", "search_intelligence",
}


class Score(BaseModel):
    overall: float = 0.0
    verdict: str = "AUDIT IN PROGRESS"
    verdict_class: Literal["critical", "moderate", "ok"] = "moderate"
    breakdown: dict[str, float] = Field(default_factory=dict)
    breakdown_labels: dict[str, str] = Field(default_factory=dict)
    breakdown_severity: dict[str, Literal["HIGH", "MEDIUM", "LOW"]] = Field(default_factory=dict)
    critical_count: int = 0
    moderate_count: int = 0
    low_count: int = 0

    @model_validator(mode="after")
    def validate_score_keys(self) -> Score:
        if self.breakdown:
            bad_keys = set(self.breakdown.keys()) - CANONICAL_SCORE_KEYS
            if bad_keys:
                raise ValueError(
                    f"score.breakdown has invalid keys: {bad_keys}. "
                    f"Only use canonical keys: {CANONICAL_SCORE_KEYS}. "
                    f"The SPA hardcodes these key names — wrong keys render as blank."
                )
        return self


# ── Case Studies ──────────────────────────────────────────────────────────────

class CaseStudy(BaseModel):
    vertical: str
    company: str
    result: str
    product: str
    why: str
    url: str  # Required — must be a live algolia.com/customers/ URL

    @field_validator("url")
    @classmethod
    def url_must_be_algolia(cls, v: str) -> str:
        if not v.startswith("http"):
            raise ValueError(f"case_studies url must be a full HTTP URL, got: '{v}'")
        return v


# ── Top-Level AuditData ───────────────────────────────────────────────────────

class Meta(BaseModel):
    company: str
    domain: str
    audit_date: str
    audited_by: str = "Algolia"
    version: str | None = None
    audit_status: str | None = None
    generated_by: str | None = None
    patch_date: str | None = None


class SearchAnalyticsMetric(BaseModel):
    key: str | None = None
    label: str | None = None
    value: str | None = None
    detail: str | None = None
    read: str | None = None
    severity: str | None = None  # high | medium | low — drives the metric-tile color
    model_config = {"extra": "allow"}


class SearchAnalyticsQuery(BaseModel):
    query: str | None = None
    volume_30d: int | None = None
    results: int | None = None
    clicks: int | None = None
    type: str | None = None
    note: str | None = None
    model_config = {"extra": "allow"}


class SearchAnalytics(BaseModel):
    """First-party Algolia telemetry for EXISTING-customer (expansion) audits.

    Powers the "Your Search, By the Numbers" SPA section. Optional — absent on
    displacement/greenfield audits, where the SPA section stays hidden.
    """

    window: str | None = None
    source_label: str | None = None
    index: str | None = None
    metrics: list[SearchAnalyticsMetric] = Field(default_factory=list)
    volume: dict[str, Any] | None = None
    zero_result_queries: list[SearchAnalyticsQuery] = Field(default_factory=list)
    no_click_queries: list[SearchAnalyticsQuery] = Field(default_factory=list)
    model_config = {"extra": "allow"}


class AuditData(BaseModel):
    """Full schema for {slug}-audit-data.json — the SPA + deliverable data contract.

    Missing required fields → ValidationError at parse time, not blank sections at render time.
    """

    meta: Meta
    score: Score = Field(default_factory=Score)
    executives: list[Executive] = Field(default_factory=list)
    intelligence_signals: list[IntelligenceSignal] = Field(default_factory=list)
    findings: list[Finding] = Field(default_factory=list)
    strategic_angles: list[StrategicAngle] = Field(default_factory=list)
    icp_mapping: ICPMapping | None = None
    abx_sequence: ABXSequence | None = None
    case_studies: list[CaseStudy] = Field(default_factory=list)
    search_analytics: SearchAnalytics | None = None

    # Allow extra fields (the contract has more fields not modeled here yet).
    model_config = {"extra": "allow"}

    @model_validator(mode="after")
    def validate_completeness_gate(self) -> AuditData:
        """COMPLETION GATE — mirrors the factcheck BLOCKED conditions."""
        if self.abx_sequence:
            for touch in self.abx_sequence.touches:
                body = touch.body or ""
                if len(body.strip()) < 50:
                    raise ValueError(
                        f"COMPLETION GATE BLOCKED: abx_sequence.touches[{touch.touch}].body "
                        f"is {len(body.strip())} chars. Run campaign-abx to generate real content."
                    )
        return self


def validate_audit_data(data: dict[str, Any]) -> tuple[bool, list[str]]:
    """Validate a dict against AuditData. Returns (is_valid, list_of_errors)."""
    from pydantic import ValidationError

    try:
        AuditData.model_validate(data)
        return True, []
    except ValidationError as e:
        errors = []
        for err in e.errors():
            loc = " → ".join(str(x) for x in err["loc"])
            errors.append(f"[{loc}] {err['msg']}")
        return False, errors
