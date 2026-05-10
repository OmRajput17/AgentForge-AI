# Changelog

All notable changes to AgentForge-AI will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.1.0] — 2026-04-30

### Added

- **Orchestrator** — LLM-powered task decomposition with confidence-based agent routing and keyword fallback
- **BaseAgent** — Abstract base class with approval gates for destructive operations
- **TriageAgent** — Full bug triage pipeline: fetch → classify → label → Notion report → Slack alert
- **StandupAgent** — Daily standup generation from GitHub activity → Notion log → Slack post
- **DevAgent** — GitHub operations agent (create issue, list issues) with structured LLM output
- **EvalEngine** — Prediction logging to JSONL with precision/recall/accuracy metrics per severity label
- **MCP Server Layer** — GitHub, Notion, and Slack API wrappers with:
  - `BaseMCPServer` abstract base class
  - Circuit breaker (3 failures → 60s cooldown)
  - Retry logic (3 attempts, exponential backoff) via `tenacity`
- **Pydantic Schemas** — `DevPlan`, `TriageItem`, `TriageResponse`, `Standup`, `Plan`, `PlanItem` for type-safe LLM output
- **Configuration System** — YAML-based config at `~/.agentforge/config.yml` with Pydantic validation
- **LLM Factory** — Pluggable provider support for OpenAI and Groq via `get_llm()`
- **Approval Gate** — Human-in-the-loop confirmation for destructive operations with auto-approve option
- **AgentLogger** — Rich console logger with per-agent color coding
- **CLI** — `agentforge init`, `agentforge run`, `agentforge server` commands via Typer
- **Full Test Suite** — 14 test modules, all fully mocked (no API keys required)
- **CI Pipeline** — GitHub Actions testing on Python 3.11 and 3.12
- **PyPI Publishing** — Automated publishing via GitHub Actions on version tags
- **MIT License**

[0.1.0]: https://github.com/OmRajput17/AgentForge-AI/releases/tag/v0.1.0
