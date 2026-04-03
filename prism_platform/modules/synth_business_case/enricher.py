"""Synth Business Case enricher -- Instructor + Claude for business case synthesis.

Takes collected upstream module outputs and synthesizes them into a complete
ROI business case using Claude for all LLM-powered generation:
1. Said vs Found matrix
2. ROI value levers
3. Displacement cost model
4. Customer proof matching
5. Timing signals with urgency
6. Executive summary + one-line pitch
"""

from __future__ import annotations

import json
from typing import Any

import structlog
from pydantic import BaseModel, ConfigDict, Field

from prism_platform.core.llm import create_completion
from prism_platform.modules.synth_business_case.schemas import (
    BusinessCaseOutput,
    CustomerProof,
    DisplacementCost,
    SaidVsFoundRow,
    TimingSignal,
    ValueLever,
)

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Instructor response models (constrain Claude output)
# ---------------------------------------------------------------------------


class SaidVsFoundSynthesis(BaseModel):
    """LLM-generated Said vs Found matrix."""

    model_config = ConfigDict(extra="forbid")

    rows: list[SaidVsFoundRow] = Field(
        description="5-7 rows of the Said vs Found matrix. Each row must have "
        "all 4 columns filled with specific, evidence-based content."
    )


class ROISynthesis(BaseModel):
    """LLM-generated ROI value levers."""

    model_config = ConfigDict(extra="forbid")

    value_levers: list[ValueLever] = Field(
        description="4-6 value levers with conservative and moderate annual USD estimates. "
        "Show all math in calculation_method. Include assumptions."
    )
    sensitivity_analysis: str = Field(
        default="",
        description="2-3 sentences on how estimates change under different assumptions.",
    )


class DisplacementSynthesis(BaseModel):
    """LLM-generated displacement cost model."""

    model_config = ConfigDict(extra="forbid")

    displacement: DisplacementCost | None = Field(
        default=None,
        description="Displacement cost model. None if no current vendor detected.",
    )


class CustomerProofSynthesis(BaseModel):
    """LLM-generated customer proof matches."""

    model_config = ConfigDict(extra="forbid")

    customer_proofs: list[CustomerProof] = Field(
        description="3-5 Algolia customer case studies matched to the prospect's value levers."
    )


class TimingSignalSynthesis(BaseModel):
    """LLM-generated timing signals with urgency."""

    model_config = ConfigDict(extra="forbid")

    timing_signals: list[TimingSignal] = Field(
        description="3-5 timing signals that create urgency for the prospect to act."
    )
    urgency_summary: str = Field(
        default="",
        description="1-2 sentence summary of why the prospect should act now.",
    )


class ExecutiveSummarySynthesis(BaseModel):
    """LLM-generated executive summary."""

    model_config = ConfigDict(extra="forbid")

    executive_summary: str = Field(
        description="2-4 paragraph executive summary tying all business case parts together. "
        "Written for a C-level audience. Include specific numbers and evidence."
    )
    one_line_pitch: str = Field(
        description="Single sentence pitch starting with the company name, e.g. "
        "'Dell can unlock $12M annual revenue by replacing Elasticsearch with Algolia.'"
    )


# ---------------------------------------------------------------------------
# Enricher class
# ---------------------------------------------------------------------------


class BusinessCaseEnricher:
    """Synthesizes upstream module outputs into a business case using Claude."""

    def __init__(self) -> None:
        pass

    async def synthesize(
        self,
        domain: str,
        company_name: str,
        raw_data: dict[str, Any],
        executive_quotes: list[str],
        financial_data: dict[str, Any],
        search_vendor: str | None,
        traffic_data: dict[str, Any],
        raw_timing_signals: list[dict[str, str]],
    ) -> tuple[BusinessCaseOutput, int, float]:
        """Synthesize all collected data into a complete business case.

        Uses 6 sequential Claude calls via Instructor for structured output.

        Args:
            domain: The prospect domain.
            company_name: The prospect company name.
            raw_data: Full upstream module output dict for context.
            executive_quotes: Extracted executive quotes.
            financial_data: Normalized financial data dict.
            search_vendor: Current search vendor name or None.
            traffic_data: Normalized traffic data dict.
            raw_timing_signals: Raw timing signals from modules.

        Returns:
            Tuple of (BusinessCaseOutput, llm_calls count, llm_cost_usd).
        """
        logger.info(
            "[BusinessCase] synthesize started",
            domain=domain,
            company_name=company_name,
            modules_with_data=sum(1 for v in raw_data.values() if v is not None),
            exec_quotes_count=len(executive_quotes),
            has_financial=financial_data.get("revenue") is not None,
            search_vendor=search_vendor,
        )

        llm_calls = 0
        llm_cost_usd = 0.0

        # Build context string shared across all prompts
        context_str = self._build_context_string(
            domain=domain,
            company_name=company_name,
            raw_data=raw_data,
            executive_quotes=executive_quotes,
            financial_data=financial_data,
            search_vendor=search_vendor,
            traffic_data=traffic_data,
        )

        # Step 1: Said vs Found matrix
        said_vs_found: list[SaidVsFoundRow] = []
        try:
            svf_result = self._call_claude(
                prompt=self._build_said_vs_found_prompt(context_str, executive_quotes),
                response_model=SaidVsFoundSynthesis,
            )
            said_vs_found = svf_result.rows
            llm_calls += 1
            llm_cost_usd += 0.005
            logger.info(
                "[BusinessCase] said_vs_found generated",
                domain=domain,
                row_count=len(said_vs_found),
            )
        except Exception as exc:
            logger.error(
                "[BusinessCase] said_vs_found generation failed",
                domain=domain,
                error=str(exc),
            )

        # Step 2: ROI value levers
        value_levers: list[ValueLever] = []
        sensitivity_analysis = ""
        try:
            roi_result = self._call_claude(
                prompt=self._build_roi_prompt(context_str, financial_data, traffic_data),
                response_model=ROISynthesis,
            )
            value_levers = roi_result.value_levers
            sensitivity_analysis = roi_result.sensitivity_analysis
            llm_calls += 1
            llm_cost_usd += 0.005
            logger.info(
                "[BusinessCase] roi levers generated",
                domain=domain,
                lever_count=len(value_levers),
            )
        except Exception as exc:
            logger.error(
                "[BusinessCase] roi generation failed",
                domain=domain,
                error=str(exc),
            )

        # Calculate totals from value levers
        total_conservative = self._sum_estimates(value_levers, "conservative_estimate")
        total_moderate = self._sum_estimates(value_levers, "moderate_estimate")

        # Step 3: Displacement cost
        displacement: DisplacementCost | None = None
        try:
            if search_vendor:
                disp_result = self._call_claude(
                    prompt=self._build_displacement_prompt(
                        context_str, search_vendor, financial_data
                    ),
                    response_model=DisplacementSynthesis,
                )
                displacement = disp_result.displacement
                llm_calls += 1
                llm_cost_usd += 0.005
                logger.info(
                    "[BusinessCase] displacement model generated",
                    domain=domain,
                    current_vendor=search_vendor,
                )
        except Exception as exc:
            logger.error(
                "[BusinessCase] displacement generation failed",
                domain=domain,
                error=str(exc),
            )

        # Step 4: Customer proofs
        customer_proofs: list[CustomerProof] = []
        try:
            proof_result = self._call_claude(
                prompt=self._build_customer_proof_prompt(
                    context_str, value_levers, raw_data.get("intel-industry")
                ),
                response_model=CustomerProofSynthesis,
            )
            customer_proofs = proof_result.customer_proofs
            llm_calls += 1
            llm_cost_usd += 0.005
            logger.info(
                "[BusinessCase] customer proofs generated",
                domain=domain,
                proof_count=len(customer_proofs),
            )
        except Exception as exc:
            logger.error(
                "[BusinessCase] customer proof generation failed",
                domain=domain,
                error=str(exc),
            )

        # Step 5: Timing signals
        timing_signals: list[TimingSignal] = []
        urgency_summary = ""
        try:
            timing_result = self._call_claude(
                prompt=self._build_timing_prompt(context_str, raw_timing_signals),
                response_model=TimingSignalSynthesis,
            )
            timing_signals = timing_result.timing_signals
            urgency_summary = timing_result.urgency_summary
            llm_calls += 1
            llm_cost_usd += 0.005
            logger.info(
                "[BusinessCase] timing signals generated",
                domain=domain,
                signal_count=len(timing_signals),
            )
        except Exception as exc:
            logger.error(
                "[BusinessCase] timing signal generation failed",
                domain=domain,
                error=str(exc),
            )

        # Step 6: Executive summary + one-line pitch
        executive_summary = ""
        one_line_pitch = ""
        try:
            exec_result = self._call_claude(
                prompt=self._build_executive_summary_prompt(
                    context_str=context_str,
                    said_vs_found=said_vs_found,
                    value_levers=value_levers,
                    total_conservative=total_conservative,
                    total_moderate=total_moderate,
                    customer_proofs=customer_proofs,
                    timing_signals=timing_signals,
                    displacement=displacement,
                ),
                response_model=ExecutiveSummarySynthesis,
            )
            executive_summary = exec_result.executive_summary
            one_line_pitch = exec_result.one_line_pitch
            llm_calls += 1
            llm_cost_usd += 0.005
            logger.info(
                "[BusinessCase] executive summary generated",
                domain=domain,
                summary_len=len(executive_summary),
            )
        except Exception as exc:
            logger.error(
                "[BusinessCase] executive summary generation failed",
                domain=domain,
                error=str(exc),
            )

        output = BusinessCaseOutput(
            domain=domain,
            said_vs_found=said_vs_found,
            value_levers=value_levers,
            total_conservative_impact=total_conservative,
            total_moderate_impact=total_moderate,
            sensitivity_analysis=sensitivity_analysis,
            displacement=displacement,
            customer_proofs=customer_proofs,
            timing_signals=timing_signals,
            urgency_summary=urgency_summary,
            executive_summary=executive_summary,
            one_line_pitch=one_line_pitch,
        )

        logger.info(
            "[BusinessCase] synthesize completed",
            domain=domain,
            llm_calls=llm_calls,
            llm_cost_usd=llm_cost_usd,
            said_vs_found_rows=len(said_vs_found),
            value_lever_count=len(value_levers),
            total_conservative=total_conservative,
            total_moderate=total_moderate,
        )

        return output, llm_calls, llm_cost_usd

    def _call_claude(
        self,
        prompt: str,
        response_model: type[BaseModel],
    ) -> Any:
        """Call Claude via Instructor with structured output.

        Args:
            prompt: The prompt string.
            response_model: Pydantic model to constrain the output.

        Returns:
            Validated Pydantic model instance.

        Raises:
            Exception: If the LLM call fails after retries.
        """
        return create_completion(
            response_model=response_model,
            max_retries=3,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
        )

    @staticmethod
    def _sum_estimates(levers: list[ValueLever], field: str) -> float | None:
        """Sum estimate values across all value levers.

        Args:
            levers: List of ValueLever instances.
            field: Which estimate field to sum ('conservative_estimate' or 'moderate_estimate').

        Returns:
            Total USD value, or None if no levers have estimates.
        """
        values = [getattr(lever, field) for lever in levers if getattr(lever, field) is not None]
        if not values:
            return None
        return sum(values)

    def _build_context_string(
        self,
        domain: str,
        company_name: str,
        raw_data: dict[str, Any],
        executive_quotes: list[str],
        financial_data: dict[str, Any],
        search_vendor: str | None,
        traffic_data: dict[str, Any],
    ) -> str:
        """Build a shared context string for all prompts.

        Args:
            domain: The prospect domain.
            company_name: The prospect company name.
            raw_data: Full upstream module output dict.
            executive_quotes: Extracted executive quotes.
            financial_data: Normalized financial data.
            search_vendor: Current search vendor.
            traffic_data: Normalized traffic data.

        Returns:
            Formatted context string.
        """
        sections: list[str] = []
        sections.append(
            f"# Prospect: {company_name} ({domain})\n"
            f"Current search vendor: {search_vendor or 'Unknown/None detected'}\n"
        )

        # Financial context
        if financial_data.get("revenue"):
            rev = financial_data["revenue"]
            growth = financial_data.get("revenue_growth_pct")
            digital = financial_data.get("digital_revenue_pct")
            ecom_rev = financial_data.get("ecommerce_revenue")
            fin_lines = [f"Revenue: ${rev:,.0f}"]
            if growth is not None:
                fin_lines.append(f"Revenue growth: {growth:.1f}%")
            if digital is not None:
                fin_lines.append(f"Digital revenue: {digital:.1f}%")
            if ecom_rev is not None:
                fin_lines.append(f"Ecommerce revenue: ${ecom_rev:,.0f}")
            sections.append("## Financial Data\n" + "\n".join(fin_lines))

        # Traffic context
        if traffic_data.get("monthly_visits"):
            traf_lines = [f"Monthly visits: {traffic_data['monthly_visits']:,}"]
            if traffic_data.get("bounce_rate") is not None:
                traf_lines.append(f"Bounce rate: {traffic_data['bounce_rate']:.1%}")
            if traffic_data.get("organic_search_pct") is not None:
                traf_lines.append(f"Organic search: {traffic_data['organic_search_pct']:.1%}")
            sections.append("## Traffic Data\n" + "\n".join(traf_lines))

        # Executive quotes
        if executive_quotes:
            sections.append(
                "## Executive Quotes\n" + "\n".join(f'- "{q}"' for q in executive_quotes[:8])
            )

        # Competitor context
        competitors_output = raw_data.get("intel-competitors")
        if competitors_output and isinstance(competitors_output, dict):
            summary = competitors_output.get("competitive_summary", "")
            golden = competitors_output.get("golden_angle_competitors", [])
            angles = competitors_output.get("top_competitive_angles", [])
            comp_lines = []
            if summary:
                comp_lines.append(f"Summary: {summary}")
            if golden:
                comp_lines.append(
                    f"Algolia customers among competitors: {', '.join(str(g) for g in golden)}"
                )
            if angles:
                for angle in angles[:3]:
                    comp_lines.append(f"- {angle}")
            if comp_lines:
                sections.append("## Competitive Landscape\n" + "\n".join(comp_lines))

        # Industry context
        industry_output = raw_data.get("intel-industry")
        if industry_output and isinstance(industry_output, dict):
            vertical = industry_output.get("vertical", "")
            benchmarks = industry_output.get("benchmarks", {})
            case_studies = industry_output.get("case_studies", [])
            ind_lines = []
            if vertical:
                ind_lines.append(f"Vertical: {vertical}")
            if benchmarks:
                ind_lines.append(f"Benchmarks: {json.dumps(benchmarks, default=str)[:500]}")
            if case_studies and isinstance(case_studies, list):
                for cs in case_studies[:3]:
                    if isinstance(cs, dict):
                        ind_lines.append(
                            f"- {cs.get('customer', 'Unknown')}: {cs.get('metric', 'N/A')}"
                        )
            if ind_lines:
                sections.append("## Industry Context\n" + "\n".join(ind_lines))

        # Company context
        company_output = raw_data.get("intel-company")
        if company_output and isinstance(company_output, dict):
            desc = company_output.get("description", "")
            employees = company_output.get("employee_count")
            hq = company_output.get("headquarters")
            co_lines = []
            if desc:
                co_lines.append(f"Description: {str(desc)[:300]}")
            if employees:
                co_lines.append(f"Employees: {employees}")
            if hq:
                co_lines.append(f"HQ: {hq}")
            if co_lines:
                sections.append("## Company Context\n" + "\n".join(co_lines))

        return "\n\n".join(sections)

    @staticmethod
    def _build_said_vs_found_prompt(
        context_str: str,
        executive_quotes: list[str],
    ) -> str:
        """Build the Said vs Found matrix generation prompt.

        Args:
            context_str: Shared context string.
            executive_quotes: Extracted executive quotes.

        Returns:
            Formatted prompt string.
        """
        quotes_section = ""
        if executive_quotes:
            quotes_section = (
                "\n\n## Available Executive Quotes (use these as 'exec_said'):\n"
                + "\n".join(f'- "{q}"' for q in executive_quotes[:10])
            )

        return (
            f"You are building a 'Said vs Found' analysis for an Algolia sales team.\n\n"
            f"{context_str}"
            f"{quotes_section}\n\n"
            f"## Instructions\n"
            f"Generate 5-7 rows of a 4-column 'Said vs Found' matrix:\n"
            f"1. exec_said: What the company's executives have publicly said (use real quotes "
            f"from above if available, otherwise synthesize realistic statements based on the "
            f"company's public posture)\n"
            f"2. we_found: What our audit data actually shows (reference specific metrics)\n"
            f"3. competitors_doing: What competitors are doing about the same topic\n"
            f"4. your_move: How Algolia specifically solves this and puts the prospect ahead\n\n"
            f"Each row must have a category tag. Use verbatim quotes with attribution when "
            f"available. Be specific with numbers and evidence."
        )

    @staticmethod
    def _build_roi_prompt(
        context_str: str,
        financial_data: dict[str, Any],
        traffic_data: dict[str, Any],
    ) -> str:
        """Build the ROI value lever generation prompt.

        Args:
            context_str: Shared context string.
            financial_data: Normalized financial data.
            traffic_data: Normalized traffic data.

        Returns:
            Formatted prompt string.
        """
        return (
            f"You are building an ROI model for an Algolia sales conversation.\n\n"
            f"{context_str}\n\n"
            f"## Instructions\n"
            f"Generate 4-6 value levers showing how Algolia creates measurable value:\n\n"
            f"Standard levers to consider:\n"
            f"1. Search Conversion Uplift -- improved search relevance drives more purchases\n"
            f"2. Revenue per Visit -- better search = higher AOV and cart sizes\n"
            f"3. Reduced Zero-Result Searches -- fewer dead ends, lower bounce\n"
            f"4. Merchandising Efficiency -- less manual curation, more automated rules\n"
            f"5. Developer Productivity -- faster integration, less maintenance\n"
            f"6. Reduced Infrastructure Cost -- managed service vs self-hosted\n\n"
            f"For each lever:\n"
            f"- Show all math in calculation_method (e.g. 'Monthly visits x search rate x "
            f"conversion lift x AOV = annual impact')\n"
            f"- conservative_estimate: use low-end industry benchmarks (e.g. 5% conversion lift)\n"
            f"- moderate_estimate: use mid-range benchmarks (e.g. 15% conversion lift)\n"
            f"- List all assumptions\n"
            f"- Reference case study proof where applicable\n\n"
            f"All estimates in annual USD. Use actual financial and traffic data provided."
        )

    @staticmethod
    def _build_displacement_prompt(
        context_str: str,
        search_vendor: str,
        financial_data: dict[str, Any],
    ) -> str:
        """Build the displacement cost model prompt.

        Args:
            context_str: Shared context string.
            search_vendor: Current search vendor name.
            financial_data: Normalized financial data.

        Returns:
            Formatted prompt string.
        """
        return (
            f"You are building a displacement cost model for an Algolia sales conversation.\n\n"
            f"{context_str}\n\n"
            f"Current search vendor to displace: {search_vendor}\n\n"
            f"## Instructions\n"
            f"Generate a displacement cost model comparing staying with {search_vendor} "
            f"vs switching to Algolia:\n\n"
            f"- cost_of_staying_annual: Total annual cost of maintaining {search_vendor} "
            f"(license + infrastructure + developer time + opportunity cost)\n"
            f"- cost_of_switching: One-time migration cost to Algolia\n"
            f"- net_benefit_3yr: 3-year net benefit of switching\n"
            f"- List all assumptions\n\n"
            f"Use industry-standard pricing estimates for {search_vendor}. "
            f"Be realistic and conservative."
        )

    @staticmethod
    def _build_customer_proof_prompt(
        context_str: str,
        value_levers: list[ValueLever],
        industry_output: dict[str, Any] | None,
    ) -> str:
        """Build the customer proof matching prompt.

        Args:
            context_str: Shared context string.
            value_levers: Generated value levers to match against.
            industry_output: Raw intel-industry output for case studies.

        Returns:
            Formatted prompt string.
        """
        lever_names = [lever.lever_name for lever in value_levers] if value_levers else []

        industry_context = ""
        if industry_output and isinstance(industry_output, dict):
            case_studies = industry_output.get("case_studies", [])
            if isinstance(case_studies, list) and case_studies:
                industry_context = "\n\n## Available Case Studies from Industry Module:\n"
                for cs in case_studies[:10]:
                    if isinstance(cs, dict):
                        industry_context += (
                            f"- {cs.get('customer', 'Unknown')}: "
                            f"{cs.get('metric', 'N/A')} "
                            f"({cs.get('industry', 'N/A')})\n"
                        )

        return (
            f"You are matching Algolia customer case studies to support a sales business case.\n\n"
            f"{context_str}"
            f"{industry_context}\n\n"
            f"Value levers to prove: {', '.join(lever_names) if lever_names else 'general value'}\n\n"
            f"## Instructions\n"
            f"Generate 3-5 Algolia customer case studies that:\n"
            f"1. Are from a similar or adjacent industry to the prospect\n"
            f"2. Demonstrate specific, measurable results\n"
            f"3. Match to the value levers identified above\n\n"
            f"Use REAL Algolia customers and metrics from public case studies. "
            f"Well-known examples: Lacoste, Under Armour, Gymshark, Staples, "
            f"Decathlon, Birkenstock, Société Générale, Twitch."
        )

    @staticmethod
    def _build_timing_prompt(
        context_str: str,
        raw_timing_signals: list[dict[str, str]],
    ) -> str:
        """Build the timing signals prompt.

        Args:
            context_str: Shared context string.
            raw_timing_signals: Raw timing signals from modules.

        Returns:
            Formatted prompt string.
        """
        signals_section = ""
        if raw_timing_signals:
            signals_section = "\n\n## Raw Signals from Intelligence Modules:\n"
            for sig in raw_timing_signals:
                signals_section += (
                    f"- [{sig.get('source_module', 'unknown')}] {sig.get('signal', 'N/A')}\n"
                )

        return (
            f"You are identifying timing signals that create urgency for an Algolia deal.\n\n"
            f"{context_str}"
            f"{signals_section}\n\n"
            f"## Instructions\n"
            f"Generate 3-5 timing signals that create urgency:\n"
            f"- Each signal should reference a specific data point from the intelligence\n"
            f"- Assign urgency: high (act within 30 days), medium (within 90 days), "
            f"low (within 6 months)\n"
            f"- source_module must be one of: intel-news, intel-hiring, intel-investor, "
            f"intel-competitors, intel-techstack, intel-traffic, intel-social\n"
            f"- Explain WHY each signal creates urgency for Algolia specifically\n\n"
            f"Also write a 1-2 sentence urgency_summary."
        )

    @staticmethod
    def _build_executive_summary_prompt(
        context_str: str,
        said_vs_found: list[SaidVsFoundRow],
        value_levers: list[ValueLever],
        total_conservative: float | None,
        total_moderate: float | None,
        customer_proofs: list[CustomerProof],
        timing_signals: list[TimingSignal],
        displacement: DisplacementCost | None,
    ) -> str:
        """Build the executive summary generation prompt.

        Args:
            context_str: Shared context string.
            said_vs_found: Generated Said vs Found rows.
            value_levers: Generated value levers.
            total_conservative: Sum of conservative estimates.
            total_moderate: Sum of moderate estimates.
            customer_proofs: Generated customer proofs.
            timing_signals: Generated timing signals.
            displacement: Displacement cost model if available.

        Returns:
            Formatted prompt string.
        """
        summary_parts: list[str] = [
            f"You are writing an executive summary for an Algolia business case.\n\n"
            f"{context_str}\n\n"
            f"## Business Case Components Already Generated:\n"
        ]

        if said_vs_found:
            summary_parts.append(f"Said vs Found: {len(said_vs_found)} insight rows generated")

        if value_levers:
            lever_names = [lv.lever_name for lv in value_levers]
            summary_parts.append(f"Value Levers: {', '.join(lever_names)}")
            if total_conservative is not None:
                summary_parts.append(f"Conservative annual impact: ${total_conservative:,.0f}")
            if total_moderate is not None:
                summary_parts.append(f"Moderate annual impact: ${total_moderate:,.0f}")

        if displacement:
            summary_parts.append(
                f"Displacement: {displacement.current_vendor} "
                f"(3yr net benefit: ${displacement.net_benefit_3yr:,.0f})"
                if displacement.net_benefit_3yr
                else f"Displacement: {displacement.current_vendor}"
            )

        if customer_proofs:
            summary_parts.append(
                f"Customer proofs: {', '.join(cp.customer_name for cp in customer_proofs)}"
            )

        if timing_signals:
            high_count = sum(1 for ts in timing_signals if ts.urgency == "high")
            summary_parts.append(
                f"Timing signals: {len(timing_signals)} total, {high_count} high-urgency"
            )

        summary_parts.append(
            "\n## Instructions\n"
            "Write a compelling executive summary (2-4 paragraphs) that:\n"
            "1. Opens with the core opportunity and total addressable value\n"
            "2. Connects executive statements to audit findings\n"
            "3. References specific competitors and customer proofs\n"
            "4. Closes with urgency and a clear call to action\n\n"
            "Also write a one_line_pitch starting with the company name.\n"
            "Example: 'Dell can unlock $12M in annual revenue by replacing "
            "Elasticsearch with Algolia NeuralSearch.'"
        )

        return "\n".join(summary_parts)
