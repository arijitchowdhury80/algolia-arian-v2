"""Contract tests for campaign-abx schemas -- 30+ pure Pydantic tests, no API/DB calls."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from prism_platform.modules.campaign_abx.schemas import (
    CampaignInput,
    CampaignOutput,
    CollateralSchedule,
    CompetitorMessaging,
    Email,
    LinkedInMessage,
    LoomScript,
)


# ---------------------------------------------------------------------------
# CampaignInput
# ---------------------------------------------------------------------------
class TestCampaignInput:
    def test_valid_input(self) -> None:
        inp = CampaignInput(domain="dell.com")
        assert inp.domain == "dell.com"

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError, match="extra_forbidden"):
            CampaignInput(domain="dell.com", bogus="nope")  # type: ignore[call-arg]

    def test_empty_domain_allowed_by_schema(self) -> None:
        """Domain validation is handled by the validator, not the schema."""
        inp = CampaignInput(domain="")
        assert inp.domain == ""


# ---------------------------------------------------------------------------
# Email
# ---------------------------------------------------------------------------
class TestEmail:
    def test_valid_full(self) -> None:
        email = Email(
            sequence_number=1,
            subject_line="Your CTO's vision for AI-powered search",
            body="Hi John, I noticed your CTO mentioned investing in AI...",
            purpose="hook",
            personalization_tokens=["CTO quote from Q4 earnings"],
            recommended_send_day="Tuesday",
            target_role="CTO",
        )
        assert email.sequence_number == 1
        assert email.purpose == "hook"
        assert len(email.personalization_tokens) == 1

    def test_minimal_defaults(self) -> None:
        email = Email(
            sequence_number=3,
            subject_line="Subject",
            body="Body text",
            purpose="proof",
        )
        assert email.personalization_tokens == []
        assert email.recommended_send_day == ""
        assert email.target_role == ""

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError, match="extra_forbidden"):
            Email(
                sequence_number=1,
                subject_line="S",
                body="B",
                purpose="hook",
                bogus="no",  # type: ignore[call-arg]
            )

    def test_rejects_invalid_purpose(self) -> None:
        with pytest.raises(ValidationError):
            Email(
                sequence_number=1,
                subject_line="S",
                body="B",
                purpose="invalid_purpose",  # type: ignore[arg-type]
            )

    def test_all_purpose_values(self) -> None:
        for purpose in ("hook", "insight", "proof", "roi", "ask"):
            email = Email(
                sequence_number=1,
                subject_line="S",
                body="B",
                purpose=purpose,  # type: ignore[arg-type]
            )
            assert email.purpose == purpose

    def test_sequence_number_zero(self) -> None:
        """Schema allows any int -- validator checks 1-5."""
        email = Email(sequence_number=0, subject_line="S", body="B", purpose="hook")
        assert email.sequence_number == 0

    def test_sequence_number_negative(self) -> None:
        email = Email(sequence_number=-1, subject_line="S", body="B", purpose="hook")
        assert email.sequence_number == -1


# ---------------------------------------------------------------------------
# LinkedInMessage
# ---------------------------------------------------------------------------
class TestLinkedInMessage:
    def test_valid_full(self) -> None:
        msg = LinkedInMessage(
            message_type="connection_request",
            target_name="Jane Smith",
            target_title="VP Engineering",
            message="Hi Jane, I noticed Dell is investing in search...",
            personalization_context="Used intel-investor exec quote",
        )
        assert msg.message_type == "connection_request"
        assert msg.target_name == "Jane Smith"

    def test_minimal_defaults(self) -> None:
        msg = LinkedInMessage(
            message_type="inmail",
            target_name="John Doe",
            target_title="CTO",
            message="Hi John...",
        )
        assert msg.personalization_context == ""

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError, match="extra_forbidden"):
            LinkedInMessage(
                message_type="inmail",
                target_name="J",
                target_title="T",
                message="M",
                bogus="no",  # type: ignore[call-arg]
            )

    def test_rejects_invalid_message_type(self) -> None:
        with pytest.raises(ValidationError):
            LinkedInMessage(
                message_type="tweet",  # type: ignore[arg-type]
                target_name="J",
                target_title="T",
                message="M",
            )

    def test_all_message_types(self) -> None:
        for mt in ("connection_request", "follow_up_1", "follow_up_2", "inmail"):
            msg = LinkedInMessage(
                message_type=mt,  # type: ignore[arg-type]
                target_name="N",
                target_title="T",
                message="M",
            )
            assert msg.message_type == mt


# ---------------------------------------------------------------------------
# LoomScript
# ---------------------------------------------------------------------------
class TestLoomScript:
    def test_valid_full(self) -> None:
        script = LoomScript(
            duration_target="2 minutes",
            opening="Hi team at Dell...",
            screen_1="Show: Dell.com search bar. Say: Here's what we found...",
            screen_2="Show: Competitor comparison chart. Say: HP uses Algolia...",
            screen_3="Show: ROI calculator. Say: We estimate $2M annual impact...",
            closing="This adds up to significant revenue opportunity.",
            call_to_action="Book a 15-minute demo at calendly.com/algolia",
        )
        assert script.duration_target == "2 minutes"
        assert "Dell" in script.opening

    def test_default_duration(self) -> None:
        script = LoomScript(
            opening="O",
            screen_1="S1",
            screen_2="S2",
            screen_3="S3",
            closing="C",
            call_to_action="CTA",
        )
        assert script.duration_target == "2 minutes"

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError, match="extra_forbidden"):
            LoomScript(
                opening="O",
                screen_1="S1",
                screen_2="S2",
                screen_3="S3",
                closing="C",
                call_to_action="CTA",
                bogus="no",  # type: ignore[call-arg]
            )

    def test_all_fields_required(self) -> None:
        """opening, screen_1, screen_2, screen_3, closing, call_to_action are required."""
        with pytest.raises(ValidationError):
            LoomScript(opening="O")  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# CollateralSchedule
# ---------------------------------------------------------------------------
class TestCollateralSchedule:
    def test_valid_full(self) -> None:
        sched = CollateralSchedule(
            week=1,
            actions=["Send Email 1", "Send LinkedIn connection request"],
            target_contacts=["Jane Smith", "John Doe"],
            notes="Focus on CTO first",
        )
        assert sched.week == 1
        assert len(sched.actions) == 2

    def test_minimal_defaults(self) -> None:
        sched = CollateralSchedule(week=3)
        assert sched.actions == []
        assert sched.target_contacts == []
        assert sched.notes == ""

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError, match="extra_forbidden"):
            CollateralSchedule(week=1, bogus="no")  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# CompetitorMessaging
# ---------------------------------------------------------------------------
class TestCompetitorMessaging:
    def test_valid_full(self) -> None:
        cm = CompetitorMessaging(
            current_vendor="Elasticsearch",
            messaging_angle="displacement",
            key_points=[
                "Elasticsearch requires dedicated engineering team to maintain",
                "Relevance tuning is manual and time-consuming",
            ],
            differentiators=[
                "Algolia provides out-of-box relevance",
                "99.999% SLA vs self-hosted",
            ],
        )
        assert cm.current_vendor == "Elasticsearch"
        assert cm.messaging_angle == "displacement"
        assert len(cm.key_points) == 2

    def test_minimal_defaults(self) -> None:
        cm = CompetitorMessaging(
            current_vendor="None/Custom",
            messaging_angle="greenfield",
        )
        assert cm.key_points == []
        assert cm.differentiators == []

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError, match="extra_forbidden"):
            CompetitorMessaging(
                current_vendor="X",
                messaging_angle="Y",
                bogus="no",  # type: ignore[call-arg]
            )


# ---------------------------------------------------------------------------
# CampaignOutput
# ---------------------------------------------------------------------------
class TestCampaignOutput:
    def test_valid_minimal(self) -> None:
        output = CampaignOutput(domain="dell.com")
        assert output.domain == "dell.com"
        assert output.emails == []
        assert output.linkedin_messages == []
        assert output.loom_script is None
        assert output.schedule == []
        assert output.competitor_messaging is None
        assert output.campaign_summary == ""
        assert output.target_contacts == []

    def test_valid_full(self) -> None:
        output = CampaignOutput(
            domain="dell.com",
            emails=[
                Email(
                    sequence_number=i,
                    subject_line=f"Subject {i}",
                    body=f"Body {i}",
                    purpose=p,
                )
                for i, p in enumerate(["hook", "insight", "proof", "roi", "ask"], start=1)
            ],
            linkedin_messages=[
                LinkedInMessage(
                    message_type="connection_request",
                    target_name="Jane",
                    target_title="CTO",
                    message="Hi Jane",
                ),
                LinkedInMessage(
                    message_type="follow_up_1",
                    target_name="Jane",
                    target_title="CTO",
                    message="Following up",
                ),
            ],
            loom_script=LoomScript(
                opening="O",
                screen_1="S1",
                screen_2="S2",
                screen_3="S3",
                closing="C",
                call_to_action="CTA",
            ),
            schedule=[
                CollateralSchedule(week=1, actions=["Email 1"]),
                CollateralSchedule(week=2, actions=["Email 2"]),
                CollateralSchedule(week=3, actions=["Email 3"]),
            ],
            competitor_messaging=CompetitorMessaging(
                current_vendor="Elasticsearch",
                messaging_angle="displacement",
            ),
            campaign_summary="Displace Elasticsearch with Algolia for $2M annual impact.",
            target_contacts=["Jane Smith", "John Doe"],
        )
        assert len(output.emails) == 5
        assert len(output.linkedin_messages) == 2
        assert output.loom_script is not None
        assert len(output.schedule) == 3
        assert output.competitor_messaging is not None
        assert output.campaign_summary != ""
        assert len(output.target_contacts) == 2

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError, match="extra_forbidden"):
            CampaignOutput(domain="dell.com", bogus="no")  # type: ignore[call-arg]

    def test_serialization_roundtrip(self) -> None:
        output = CampaignOutput(
            domain="dell.com",
            emails=[
                Email(
                    sequence_number=1,
                    subject_line="S",
                    body="B",
                    purpose="hook",
                )
            ],
            campaign_summary="Test summary",
        )
        data = output.model_dump()
        restored = CampaignOutput.model_validate(data)
        assert restored.domain == "dell.com"
        assert len(restored.emails) == 1
        assert restored.campaign_summary == "Test summary"

    def test_json_roundtrip(self) -> None:
        output = CampaignOutput(domain="dell.com")
        json_str = output.model_dump_json()
        restored = CampaignOutput.model_validate_json(json_str)
        assert restored.domain == "dell.com"
