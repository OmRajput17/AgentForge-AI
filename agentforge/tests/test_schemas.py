# agentforge/tests/test_schemas.py
"""Unit tests for Pydantic LLM response schemas."""

import pytest
from agentforge.agents.schemas import (
    DevPlan,
    TriageItem,
    TriageResponse,
    Standup,
)


# ═══════════════════════════════════════════════════════════════════
# DevPlan
# ═══════════════════════════════════════════════════════════════════

class TestDevPlan:

    def test_action_lowercased(self):
        plan = DevPlan(action="CREATE_ISSUE", title="t", body="b")
        assert plan.action == "create_issue"

    def test_action_stripped(self):
        plan = DevPlan(action="  List_Issues  ", title="t", body="b")
        assert plan.action == "list_issues"

    def test_default_path(self):
        plan = DevPlan(action="read_repo", title="t", body="b")
        assert plan.path == ""

    def test_explicit_path(self):
        plan = DevPlan(action="read_repo", title="t", body="b", path="src/main.py")
        assert plan.path == "src/main.py"


# ═══════════════════════════════════════════════════════════════════
# TriageItem
# ═══════════════════════════════════════════════════════════════════

class TestTriageItem:

    def test_valid_severity(self):
        item = TriageItem(number=1, severity="high", reason="broken")
        assert item.severity == "high"

    def test_severity_lowercased(self):
        item = TriageItem(number=1, severity="HIGH")
        assert item.severity == "high"

    def test_severity_stripped(self):
        item = TriageItem(number=1, severity="  Medium  ")
        assert item.severity == "medium"

    def test_invalid_severity_defaults_to_low(self):
        item = TriageItem(number=1, severity="URGENT")
        assert item.severity == "low"

    def test_empty_severity_defaults_to_low(self):
        item = TriageItem(number=1, severity="")
        assert item.severity == "low"

    def test_default_reason(self):
        item = TriageItem(number=1, severity="low")
        assert item.reason == ""

    def test_all_valid_severities(self):
        for sev in ("critical", "high", "medium", "low"):
            item = TriageItem(number=1, severity=sev)
            assert item.severity == sev


# ═══════════════════════════════════════════════════════════════════
# TriageResponse
# ═══════════════════════════════════════════════════════════════════

class TestTriageResponse:

    def test_wraps_list(self):
        resp = TriageResponse(items=[
            TriageItem(number=1, severity="high", reason="bad"),
            TriageItem(number=2, severity="low", reason="minor"),
        ])
        assert len(resp.items) == 2
        assert resp.items[0].number == 1
        assert resp.items[1].severity == "low"

    def test_empty_list(self):
        resp = TriageResponse(items=[])
        assert resp.items == []

    def test_model_dump(self):
        resp = TriageResponse(items=[
            TriageItem(number=1, severity="critical", reason="data loss"),
        ])
        dumped = resp.items[0].model_dump()
        assert dumped == {"number": 1, "severity": "critical", "reason": "data loss"}


# ═══════════════════════════════════════════════════════════════════
# Standup
# ═══════════════════════════════════════════════════════════════════

class TestStandup:

    def test_all_fields(self):
        s = Standup(yesterday="did stuff", today="will do stuff", blockers="None")
        assert s.yesterday == "did stuff"
        assert s.today == "will do stuff"
        assert s.blockers == "None"

    def test_empty_strings(self):
        s = Standup(yesterday="", today="", blockers="")
        assert s.yesterday == ""
