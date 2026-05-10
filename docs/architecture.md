# Architecture Guide

Deep dive into AgentForge-AI's system design, component interactions, and design decisions.

## System Overview

AgentForge follows a **decompose → route → execute → report** pattern:

```
User Input (plain English)
    │
    ▼
┌──────────────────────┐
│     Orchestrator      │  ← LLM decomposes task, scores confidence
│  Keyword Fallback     │  ← Reliability layer for low-confidence routing
│  Parallel Scheduler   │  ← asyncio.gather() for concurrent subtasks
└──────────┬───────────┘
    ┌──────┼──────────┐
    ▼      ▼          ▼
 DevAgent  TriageAg  StandupAg   ← Specialized agents
    │         │         │
    ▼         ▼         ▼
┌────────────────────────────┐
│     MCP Server Layer       │  ← GitHub, Notion, Slack (resilient)
│  Circuit Breaker + Retry   │
└────────────────────────────┘
```

## Core Components

### Orchestrator (`orchestrator.py`)

Central coordinator. Receives a user task and manages the entire lifecycle:

1. **Decompose** — LLM breaks task into subtasks using `with_structured_output(Plan)`
2. **Route** — Each subtask gets a confidence score. Below `confidence_threshold` → keyword fallback
3. **Schedule** — Subtasks marked `parallel: true` run via `asyncio.gather()`, others run sequentially
4. **Collect** — Results aggregated into `AgentForgeState`, audit log accumulated

### BaseAgent (`agents/base.py`)

Abstract base class. All agents extend this. Key pattern:

```
run(subtask, state)
  ├── if destructive → ApprovalGate.ask()
  │     ├── Approved → continue
  │     └── Rejected → return {success: False}
  ├── execute(subtask, state)  ← subclass implementation
  └── Log result
```

**Return contract** — every `execute()` returns:
```python
{'output': str, 'success': bool, 'actions_taken': list[str]}
```

### TriageAgent (`agents/triage_agent.py`)

8-step pipeline: fetch → batch classify → log to EvalEngine → approval gate → apply labels → Notion report → Slack alert → print metrics.

**Key decisions:**
- Batch classification (1 LLM call for all issues = 90% cost reduction)
- Predictions logged BEFORE actions (audit trail)
- Per-issue resilience for label application
- Notion/Slack failures are non-fatal

### StandupAgent (`agents/standup_agent.py`)

Reads GitHub events → summarizes activity → LLM generates structured standup → posts to Notion + Slack.

Handles: `PushEvent`, `PullRequestEvent`, `IssueEvent`, `IssueCommentEvent`.

### DevAgent (`agents/dev_agent.py`)

LLM interprets subtask into `DevPlan` (action, title, body). Supports `create_issue` and `list_issues`.

## MCP Server Layer

### BaseMCPServer (`mcp/base.py`)

All servers inherit resilient `_resilient_get()` / `_resilient_post()`:

- **Retry**: 3 attempts, exponential backoff (2s → 4s → 10s) via `tenacity`
- **Circuit Breaker**: Opens after 3 consecutive failures, resets after 60s

Circuit breaker states: **Closed** → (3 failures) → **Open** → (60s) → **Half-Open** → (success) → **Closed**

### Available Servers

| Server | API | Key Methods |
|--------|-----|-------------|
| `GitHubMCPServer` | GitHub REST v3 | `create_issue`, `list_issues`, `add_labels`, `get_user_activity` |
| `NotionMCPServer` | Notion API v1 | `create_page`, `search_page` |
| `SlackMCPServer` | Slack Web API | `send_message`, `list_channels` |

## State Management

`AgentForgeState` (TypedDict) flows through the pipeline:

| Field | Type | Purpose |
|-------|------|---------|
| `task` | `str` | Original user input |
| `subtasks` | `list` | Decomposed subtask list |
| `results` | `list[dict]` | Per-agent results |
| `audit_log` | `list[str]` | All actions taken |
| `iteration` | `int` | Loop guard |
| `completed` | `bool` | Completion flag |

## Async Model

MCP servers use synchronous `httpx.Client`. Agent code wraps these in `asyncio.to_thread()` to avoid blocking the event loop. Parallel subtasks use `asyncio.gather(return_exceptions=True)`.

## Error Handling

| Layer | Strategy |
|-------|----------|
| LLM calls | `try/except` → safe fallback (e.g., `"low"` severity) |
| MCP writes | Per-item resilience |
| Notion/Slack | Non-fatal (logged as warning) |
| Orchestrator | `return_exceptions=True` in gather |
| Agent routing | Keyword fallback for low confidence |
