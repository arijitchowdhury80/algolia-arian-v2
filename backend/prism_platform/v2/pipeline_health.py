"""Pipeline health tracking — captures every failure, fallback, and degradation.

Every module execution produces a PipelineHealthLog that records:
- What was attempted at each step
- What succeeded, what failed, what fell back
- Which tiers were used and which were unavailable
- Data quality warnings (low exec count, missing fields, conflicting sources)

This log is attached to the final output so the end user sees exactly
what happened — no silent failures, no hidden degradations.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class EventSeverity(str, Enum):
    """How serious is this event?"""

    INFO = "info"          # Normal operation, just tracking
    WARNING = "warning"    # Degraded but continuing (e.g., page not found, tier fallback)
    ERROR = "error"        # Something failed (e.g., API error, schema validation failure)
    CRITICAL = "critical"  # Track completely failed, output affected


class EventCategory(str, Enum):
    """What part of the pipeline produced this event?"""

    TRACK1_WEBFETCH = "track1_webfetch"
    TRACK2_PERPLEXITY = "track2_perplexity"
    TRACK3_SYNTHESIS = "track3_synthesis"
    CACHE = "cache"
    DB_PERSIST = "db_persist"
    VALIDATION = "validation"


class PipelineEvent(BaseModel):
    """A single event in the pipeline execution."""

    model_config = ConfigDict(frozen=True)

    timestamp: str = Field(
        default_factory=lambda: datetime.now(UTC).isoformat(),
    )
    category: EventCategory
    severity: EventSeverity
    message: str = Field(description="Human-readable description of what happened")
    detail: dict[str, Any] = Field(
        default_factory=dict,
        description="Structured detail — URLs tried, error messages, tier used, etc.",
    )


class PipelineHealthLog:
    """Accumulates pipeline events across all tracks.

    Usage:
        health = PipelineHealthLog(module_name="intel-company", domain="nike.com")
        health.info("track1_webfetch", "Fetching leadership page", url="https://...")
        health.warning("track1_webfetch", "Leadership page not found", paths_tried=14)
        health.error("track2_perplexity", "API call failed", error="timeout")

        # At the end:
        health.summary()  # → dict for JSON output
        health.to_markdown()  # → string for report
    """

    def __init__(self, module_name: str, domain: str) -> None:
        self.module_name = module_name
        self.domain = domain
        self.events: list[PipelineEvent] = []
        self._start_time = datetime.now(UTC)

    def info(self, category: str, message: str, **detail: Any) -> None:
        self._add(EventSeverity.INFO, category, message, detail)

    def warning(self, category: str, message: str, **detail: Any) -> None:
        self._add(EventSeverity.WARNING, category, message, detail)

    def error(self, category: str, message: str, **detail: Any) -> None:
        self._add(EventSeverity.ERROR, category, message, detail)

    def critical(self, category: str, message: str, **detail: Any) -> None:
        self._add(EventSeverity.CRITICAL, category, message, detail)

    def _add(
        self, severity: EventSeverity, category: str, message: str, detail: dict
    ) -> None:
        self.events.append(
            PipelineEvent(
                category=EventCategory(category),
                severity=severity,
                message=message,
                detail=detail,
            )
        )

    @property
    def has_errors(self) -> bool:
        return any(e.severity in (EventSeverity.ERROR, EventSeverity.CRITICAL) for e in self.events)

    @property
    def has_warnings(self) -> bool:
        return any(e.severity == EventSeverity.WARNING for e in self.events)

    @property
    def overall_status(self) -> str:
        """Overall pipeline health: HEALTHY, DEGRADED, or FAILED."""
        if any(e.severity == EventSeverity.CRITICAL for e in self.events):
            return "FAILED"
        if any(e.severity in (EventSeverity.ERROR, EventSeverity.WARNING) for e in self.events):
            return "DEGRADED"
        return "HEALTHY"

    def events_by_category(self, category: str) -> list[PipelineEvent]:
        return [e for e in self.events if e.category.value == category]

    def summary(self) -> dict[str, Any]:
        """Structured summary for JSON output."""
        elapsed = (datetime.now(UTC) - self._start_time).total_seconds()
        return {
            "module": self.module_name,
            "domain": self.domain,
            "overall_status": self.overall_status,
            "total_duration_seconds": round(elapsed, 1),
            "event_counts": {
                "info": sum(1 for e in self.events if e.severity == EventSeverity.INFO),
                "warning": sum(1 for e in self.events if e.severity == EventSeverity.WARNING),
                "error": sum(1 for e in self.events if e.severity == EventSeverity.ERROR),
                "critical": sum(1 for e in self.events if e.severity == EventSeverity.CRITICAL),
            },
            "events": [
                {
                    "timestamp": e.timestamp,
                    "category": e.category.value,
                    "severity": e.severity.value,
                    "message": e.message,
                    "detail": e.detail,
                }
                for e in self.events
                if e.severity != EventSeverity.INFO  # Only non-info in JSON to keep it focused
            ],
        }

    def to_markdown(self) -> str:
        """Render pipeline health as markdown for the report.

        Shows: overall status, what happened at each track,
        and all warnings/errors with detail.
        """
        lines = []
        status = self.overall_status
        status_icon = {"HEALTHY": "PASS", "DEGRADED": "DEGRADED", "FAILED": "FAILED"}[status]
        lines.append(f"## Pipeline Health: {status_icon}")
        lines.append("")

        # Track-by-track summary
        for track, label in [
            ("track1_webfetch", "Track 1 — WebFetch"),
            ("track2_perplexity", "Track 2 — Perplexity"),
            ("track3_synthesis", "Track 3 — Synthesis"),
        ]:
            track_events = self.events_by_category(track)
            if not track_events:
                lines.append(f"### {label}")
                lines.append("No events recorded.")
                lines.append("")
                continue

            worst = max(track_events, key=lambda e: list(EventSeverity).index(e.severity))
            track_status = worst.severity.value.upper()
            lines.append(f"### {label} [{track_status}]")

            for event in track_events:
                if event.severity == EventSeverity.INFO:
                    lines.append(f"- {event.message}")
                else:
                    severity_tag = event.severity.value.upper()
                    lines.append(f"- **[{severity_tag}]** {event.message}")
                    if event.detail:
                        for k, v in event.detail.items():
                            lines.append(f"  - {k}: {v}")
            lines.append("")

        # Validation warnings
        validation_events = self.events_by_category("validation")
        if validation_events:
            lines.append("### Data Quality Warnings")
            for event in validation_events:
                severity_tag = event.severity.value.upper()
                lines.append(f"- **[{severity_tag}]** {event.message}")
                if event.detail:
                    for k, v in event.detail.items():
                        lines.append(f"  - {k}: {v}")
            lines.append("")

        # DB persist
        db_events = self.events_by_category("db_persist")
        if db_events:
            for event in db_events:
                if event.severity != EventSeverity.INFO:
                    lines.append(f"**[{event.severity.value.upper()}]** DB: {event.message}")

        return "\n".join(lines)
