"""Intel Competitors enricher -- Instructor + Claude for competitive intelligence synthesis.

Takes collected upstream module outputs and synthesizes them into a unified
competitive analysis using Claude for the LLM-powered portions (competitive
positioning, scenario determination, and summary generation).
"""

from __future__ import annotations

from typing import Any

import structlog
from pydantic import BaseModel, ConfigDict, Field

from prism_platform.core.llm import create_completion
from prism_platform.modules.intel_competitors.schemas import (
    CompetitiveScenario,
    CompetitorsOutput,
    ExecutiveSentiment,
    FinancialComparison,
    HiringComparison,
    TechComparison,
    TrafficComparison,
)

logger = structlog.get_logger(__name__)


class CompetitiveSynthesis(BaseModel):
    """LLM-generated competitive synthesis output.

    This is the Pydantic model used with Instructor to constrain the LLM output.
    """

    model_config = ConfigDict(extra="forbid")

    competitive_position: str = Field(
        description="One of: leader, fast_follower, laggard, unknown. "
        "Based on technology adoption, traffic scale, financial strength, and hiring signals."
    )
    competitive_pressure: str = Field(
        description="One of: increasing, stable, decreasing, unknown. "
        "Based on competitor tech investments, hiring trends, and executive sentiment."
    )
    scenario_type: str = Field(
        description="One of: golden, offensive, defensive, displacement. "
        "'golden' = competitor uses Algolia, proving value in the vertical. "
        "'offensive' = prospect is behind competitors and needs to catch up. "
        "'defensive' = prospect is a leader being chased. "
        "'displacement' = prospect uses a competitor's search vendor we can replace."
    )
    scenario_description: str = Field(
        description="1-3 sentence description of the competitive scenario and why it matters."
    )
    scenario_evidence: list[str] = Field(
        default_factory=list,
        description="Specific evidence points supporting this scenario assessment.",
    )
    recommended_play: str = Field(
        default="",
        description="Recommended sales play based on the competitive landscape.",
    )
    competitive_summary: str = Field(
        description="2-4 sentence executive summary of the competitive landscape. "
        "Focus on what matters for an Algolia sales conversation."
    )
    top_competitive_angles: list[str] = Field(
        default_factory=list,
        description="Top 3-5 competitive angles for Algolia sales. "
        "Each angle should be a concise, actionable talking point.",
    )


class CompetitorsEnricher:
    """Synthesizes upstream module outputs into competitive intelligence using Claude."""

    def __init__(self) -> None:
        pass

    async def synthesize(
        self,
        domain: str,
        company_name: str,
        tech_comparisons: list[TechComparison],
        traffic_comparisons: list[TrafficComparison],
        financial_comparisons: list[FinancialComparison],
        hiring_comparisons: list[HiringComparison],
        executive_sentiments: list[ExecutiveSentiment],
        golden_angle_competitors: list[str],
        tech_gaps: list[str],
        raw_data: dict[str, Any],
    ) -> tuple[CompetitorsOutput, int, float]:
        """Synthesize all extracted comparisons into competitive intelligence.

        Uses Claude via Instructor to determine competitive positioning,
        scenario type, and generate summary / angles.

        Args:
            domain: The prospect domain.
            company_name: The prospect company name.
            tech_comparisons: Extracted technology comparisons.
            traffic_comparisons: Extracted traffic comparisons.
            financial_comparisons: Extracted financial comparisons.
            hiring_comparisons: Extracted hiring comparisons.
            executive_sentiments: Extracted executive sentiment data.
            golden_angle_competitors: Competitors known to use Algolia.
            tech_gaps: Identified technology gaps.
            raw_data: Full upstream module output dict for context.

        Returns:
            Tuple of (CompetitorsOutput, llm_calls count, llm_cost_usd).
        """
        logger.info(
            "[Competitors] synthesize started",
            domain=domain,
            tech_count=len(tech_comparisons),
            traffic_count=len(traffic_comparisons),
            financial_count=len(financial_comparisons),
            hiring_count=len(hiring_comparisons),
            sentiment_count=len(executive_sentiments),
        )

        llm_calls = 0
        llm_cost_usd = 0.0

        # Build the context prompt for the LLM
        prompt = self._build_synthesis_prompt(
            domain=domain,
            company_name=company_name,
            tech_comparisons=tech_comparisons,
            traffic_comparisons=traffic_comparisons,
            financial_comparisons=financial_comparisons,
            hiring_comparisons=hiring_comparisons,
            executive_sentiments=executive_sentiments,
            golden_angle_competitors=golden_angle_competitors,
            tech_gaps=tech_gaps,
        )

        # Call Claude for synthesis
        try:
            synthesis = create_completion(
                response_model=CompetitiveSynthesis,
                max_retries=3,
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
            )
            llm_calls = 1
            # Approximate cost: Claude Sonnet is very inexpensive
            llm_cost_usd = 0.005

            logger.info(
                "[Competitors] Claude synthesis completed",
                domain=domain,
                position=synthesis.competitive_position,
                scenario=synthesis.scenario_type,
                angles_count=len(synthesis.top_competitive_angles),
            )

        except Exception as exc:
            logger.error(
                "[Competitors] Claude synthesis failed, using fallback",
                domain=domain,
                error=str(exc),
            )
            synthesis = self._fallback_synthesis(
                golden_angle_competitors=golden_angle_competitors,
                tech_gaps=tech_gaps,
                tech_comparisons=tech_comparisons,
            )

        # Validate scenario_type and competitive_position literals
        valid_positions = {"leader", "fast_follower", "laggard", "unknown"}
        valid_pressures = {"increasing", "stable", "decreasing", "unknown"}
        valid_scenarios = {"golden", "offensive", "defensive", "displacement"}

        position = (
            synthesis.competitive_position
            if synthesis.competitive_position in valid_positions
            else "unknown"
        )
        pressure = (
            synthesis.competitive_pressure
            if synthesis.competitive_pressure in valid_pressures
            else "unknown"
        )
        scenario_type = (
            synthesis.scenario_type
            if synthesis.scenario_type in valid_scenarios
            else "displacement"
        )

        scenario = CompetitiveScenario(
            scenario_type=scenario_type,  # type: ignore[arg-type]
            description=synthesis.scenario_description,
            evidence=synthesis.scenario_evidence,
            recommended_play=synthesis.recommended_play,
        )

        output = CompetitorsOutput(
            domain=domain,
            tech_comparisons=tech_comparisons,
            golden_angle_competitors=golden_angle_competitors,
            tech_gaps=tech_gaps,
            traffic_comparisons=traffic_comparisons,
            financial_comparisons=financial_comparisons,
            hiring_comparisons=hiring_comparisons,
            executive_sentiments=executive_sentiments,
            competitive_position=position,  # type: ignore[arg-type]
            competitive_pressure=pressure,  # type: ignore[arg-type]
            competitive_scenario=scenario,
            competitive_summary=synthesis.competitive_summary,
            top_competitive_angles=synthesis.top_competitive_angles,
        )

        logger.info(
            "[Competitors] synthesize completed",
            domain=domain,
            position=position,
            pressure=pressure,
            scenario_type=scenario_type,
            llm_calls=llm_calls,
        )

        return output, llm_calls, llm_cost_usd

    def _build_synthesis_prompt(
        self,
        domain: str,
        company_name: str,
        tech_comparisons: list[TechComparison],
        traffic_comparisons: list[TrafficComparison],
        financial_comparisons: list[FinancialComparison],
        hiring_comparisons: list[HiringComparison],
        executive_sentiments: list[ExecutiveSentiment],
        golden_angle_competitors: list[str],
        tech_gaps: list[str],
    ) -> str:
        """Build the synthesis prompt from extracted comparisons.

        Args:
            domain: The prospect domain.
            company_name: The prospect company name.
            tech_comparisons: Technology comparison data.
            traffic_comparisons: Traffic comparison data.
            financial_comparisons: Financial comparison data.
            hiring_comparisons: Hiring comparison data.
            executive_sentiments: Executive sentiment data.
            golden_angle_competitors: Competitors using Algolia.
            tech_gaps: Identified technology gaps.

        Returns:
            Formatted prompt string for the LLM.
        """
        sections: list[str] = []
        sections.append(
            f"You are analyzing the competitive landscape for {company_name} ({domain}) "
            f"to support an Algolia sales conversation.\n"
        )

        # Technology section
        if tech_comparisons:
            tech_lines = ["## Technology Comparison"]
            for tc in tech_comparisons:
                vendor = tc.search_vendor or "None detected"
                ecom = tc.ecommerce_platform or "None detected"
                algolia_flag = " [USES ALGOLIA]" if tc.algolia_detected else ""
                tech_lines.append(
                    f"- {tc.company_name} ({tc.domain}): Search={vendor}, "
                    f"Ecommerce={ecom}, Techs={len(tc.key_technologies)}{algolia_flag}"
                )
            sections.append("\n".join(tech_lines))

        if golden_angle_competitors:
            sections.append(
                f"## Golden Angle\nCompetitors using Algolia: {', '.join(golden_angle_competitors)}"
            )

        if tech_gaps:
            sections.append("## Tech Gaps\n" + "\n".join(f"- {g}" for g in tech_gaps))

        # Traffic section
        if traffic_comparisons:
            traffic_lines = ["## Traffic Comparison"]
            for tc in traffic_comparisons:
                visits = f"{tc.monthly_visits:,}" if tc.monthly_visits else "N/A"
                bounce = f"{tc.bounce_rate:.1%}" if tc.bounce_rate is not None else "N/A"
                trend = tc.growth_trend or "N/A"
                traffic_lines.append(
                    f"- {tc.company_name} ({tc.domain}): Visits={visits}, "
                    f"Bounce={bounce}, Trend={trend}"
                )
            sections.append("\n".join(traffic_lines))

        # Financial section
        if financial_comparisons:
            fin_lines = ["## Financial Comparison"]
            for fc in financial_comparisons:
                rev = f"${fc.revenue:,.0f}" if fc.revenue else "N/A"
                growth = (
                    f"{fc.revenue_growth_pct:.1f}%" if fc.revenue_growth_pct is not None else "N/A"
                )
                fin_lines.append(
                    f"- {fc.company_name} ({fc.domain}): Revenue={rev}, Growth={growth}"
                )
            sections.append("\n".join(fin_lines))

        # Hiring section
        if hiring_comparisons:
            hire_lines = ["## Hiring Comparison"]
            for hc in hiring_comparisons:
                hire_lines.append(
                    f"- {hc.company_name} ({hc.domain}): "
                    f"Total Roles={hc.total_open_roles}, "
                    f"Search Roles={hc.search_related_roles}, "
                    f"Build vs Buy={hc.build_vs_buy or 'N/A'}, "
                    f"Trend={hc.hiring_trend or 'N/A'}"
                )
            sections.append("\n".join(hire_lines))

        # Executive sentiment section
        if executive_sentiments:
            exec_lines = ["## Executive Sentiment"]
            for es in executive_sentiments:
                exec_lines.append(
                    f"- {es.company_name}: Commitment={es.digital_commitment_level}, "
                    f"Search Mentions={es.search_mentions}"
                )
                for q in es.key_quotes[:3]:
                    exec_lines.append(f'  Quote: "{q}"')
            sections.append("\n".join(exec_lines))

        sections.append(
            "\n## Instructions\n"
            "Based on this data, determine:\n"
            "1. The prospect's competitive position (leader/fast_follower/laggard/unknown)\n"
            "2. Competitive pressure direction (increasing/stable/decreasing/unknown)\n"
            "3. The best competitive scenario (golden/offensive/defensive/displacement)\n"
            "4. A 2-4 sentence competitive summary for Algolia sales\n"
            "5. Top 3-5 competitive angles as actionable talking points\n"
            "6. Evidence supporting the scenario\n"
            "7. A recommended sales play\n"
            "\nBe specific and reference actual data points. "
            "If data is missing, use 'unknown' rather than making assumptions."
        )

        return "\n\n".join(sections)

    @staticmethod
    def _fallback_synthesis(
        golden_angle_competitors: list[str],
        tech_gaps: list[str],
        tech_comparisons: list[TechComparison],
    ) -> CompetitiveSynthesis:
        """Generate a basic synthesis when LLM call fails.

        Args:
            golden_angle_competitors: Competitors using Algolia.
            tech_gaps: Identified technology gaps.
            tech_comparisons: Technology comparisons.

        Returns:
            CompetitiveSynthesis with conservative/safe defaults.
        """
        if golden_angle_competitors:
            scenario_type = "golden"
            description = (
                f"Competitors {', '.join(golden_angle_competitors)} already use Algolia, "
                "proving value in this vertical."
            )
            recommended_play = "Reference competitor success with Algolia to build credibility."
        elif tech_gaps:
            scenario_type = "offensive"
            description = "Prospect lags behind competitors in search technology adoption."
            recommended_play = "Position Algolia as the solution to close the technology gap."
        else:
            scenario_type = "displacement"
            description = "Competitive landscape assessment requires more data for precision."
            recommended_play = "Conduct deeper discovery to identify specific pain points."

        angles: list[str] = []
        if golden_angle_competitors:
            angles.append(
                f"Golden Angle: {', '.join(golden_angle_competitors)} already trust Algolia"
            )
        if tech_gaps:
            for gap in tech_gaps[:2]:
                angles.append(f"Tech Gap: {gap}")
        if not angles:
            angles.append("Explore search and discovery improvement opportunities")

        return CompetitiveSynthesis(
            competitive_position="unknown",
            competitive_pressure="unknown",
            scenario_type=scenario_type,
            scenario_description=description,
            scenario_evidence=tech_gaps[:3] if tech_gaps else [],
            recommended_play=recommended_play,
            competitive_summary=(
                f"Competitive analysis is based on limited data. "
                f"{len(tech_comparisons)} companies compared on technology stack."
            ),
            top_competitive_angles=angles,
        )
