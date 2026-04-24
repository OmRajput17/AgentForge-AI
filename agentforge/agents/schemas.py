# agentforge/agents/schemas.py
"""
Pydantic models for structured LLM output across all agents.

These schemas are used with LangChain's `with_structured_output()` to replace
unsafe `json.loads(resp.content)` parsing.  Validators embedded in the models
guarantee normalised, type-safe data at parse time.
"""

from pydantic import BaseModel, field_validator


# ── DevAgent ────────────────────────────────────────────────────────

class DevPlan(BaseModel):
    """Structured LLM response for DevAgent GitHub operations."""
    action: str
    title: str
    body: str
    path: str = ""

    @field_validator("action")
    @classmethod
    def normalize_action(cls, v: str) -> str:
        return v.strip().lower()


# ── TriageAgent ─────────────────────────────────────────────────────

VALID_SEVERITIES = frozenset({"critical", "high", "medium", "low", "wontfix"})


class TriageItem(BaseModel):
    """Single classified issue with severity."""
    issue_number: int
    severity: str
    confidence: float = 1.0
    reason: str = ""

    @field_validator("severity")
    @classmethod
    def normalize_severity(cls, v: str) -> str:
        v = v.strip().lower()
        return v if v in VALID_SEVERITIES else "low"


class TriageResponse(BaseModel):
    """Wrapper for a list of triage items.

    Using a wrapper instead of RootModel keeps compatibility with
    LangChain's `with_structured_output()` which expects a regular
    BaseModel with named fields.
    """
    items: list[TriageItem]


# ── StandupAgent ────────────────────────────────────────────────────

class Standup(BaseModel):
    """Structured LLM response for daily standup generation."""
    yesterday: str
    today: str
    blockers: str

# ── Orchestrator ────────────────────────────────────────────────────

class PlanItem(BaseModel):
    agent: str
    subtask: str
    confidence: float
    parallel: bool

class Plan(BaseModel):
    items: list[PlanItem]