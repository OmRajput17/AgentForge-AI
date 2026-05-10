# API Reference

Complete reference for all public classes, methods, and schemas in AgentForge-AI.

## Table of Contents

- [CLI Commands](#cli-commands)
- [Configuration](#configuration)
- [Orchestrator](#orchestrator)
- [Agents](#agents)
- [MCP Servers](#mcp-servers)
- [EvalEngine](#evalengine)
- [Schemas](#schemas)
- [Utilities](#utilities)

---

## CLI Commands

Module: `agentforge.cli`

### `agentforge init`

Initialize config at `~/.agentforge/config.yml`. Safe to run multiple times.

### `agentforge run <task>`

Run a multi-agent workflow. `task` is a plain-English string.

### `agentforge server`

Display MCP server connection status (configured/not configured).

---

## Configuration

Module: `agentforge.config`

### `Settings`

Top-level Pydantic model for all configuration.

| Field | Type | Default |
|-------|------|---------|
| `llm` | `LLMConfig` | See below |
| `mcp_servers` | `MCPServerConfig` | See below |
| `auto_approve` | `bool` | `False` |
| `confidence_threshold` | `float` | `0.8` |
| `max_iterations` | `int` | `10` |
| `standup_lookback_hours` | `int` | `24` |

### `LLMConfig`

| Field | Type | Default |
|-------|------|---------|
| `provider` | `str` | `"openai"` |
| `model` | `str` | `"gpt-4o"` |
| `api_key` | `str` | `""` |

### `MCPServerConfig`

| Field | Type | Default |
|-------|------|---------|
| `github_token` | `str` | `""` |
| `github_owner` | `str` | `""` |
| `github_repo` | `str` | `""` |
| `notion_token` | `str` | `""` |
| `notion_page_id` | `str` | `""` |
| `slack_token` | `str` | `""` |
| `slack_channel` | `str` | `"general"` |

### `get_settings() → Settings`

Returns the singleton `Settings` instance. Loads from `~/.agentforge/config.yml` if it exists, otherwise returns defaults. Cached via `@lru_cache`.

### `get_llm(temperature: float = 0)`

Factory function. Returns `ChatGroq` or `ChatOpenAI` based on `Settings.llm.provider`.

### `init_config()`

Creates `~/.agentforge/config.yml` with default values if it doesn't exist.

---

## Orchestrator

Module: `agentforge.orchestrator`

### `class Orchestrator`

#### `__init__()`

Initializes LLM, logger, and loads confidence threshold from settings.

#### `async run(task: str) → None`

Main entry point. Decomposes task → schedules subtasks → executes agents → prints summary.

#### `async _decompose(task: str) → list[dict]`

Uses LLM with `with_structured_output(Plan)` to break task into subtasks. Returns list of dicts with keys: `agent`, `subtask`, `confidence`, `parallel`.

#### `_keyword_route(subtask: str) → str | None`

Keyword fallback router. Returns agent name if keywords match, else `None`.

#### `async _run_subtasks(item: dict, state: AgentForgeState) → dict`

Instantiates the appropriate agent and calls `agent.run()`. Returns result dict.

### Constants

**`AGENT_REGISTRY`** — Maps agent names to classes:
```python
{"dev": DevAgent, "triage": TriageAgent, "standup": StandupAgent}
```

**`KEYWORD_MAPPING`** — Fallback keywords per agent:
```python
{
    "triage": ["triage", "bug", "severity", "label", "issues"],
    "standup": ["standup", "stand-up", "daily", "yesterday", "today"],
    "dev": ["create issue", "github issue", "pull request", "commit"],
}
```

---

## Agents

### `class BaseAgent(ABC)`

Module: `agentforge.agents.base`

#### `__init__(name: str, destructive: bool = False)`

| Param | Description |
|-------|-------------|
| `name` | Agent identifier (used for logging and registry) |
| `destructive` | If `True`, triggers approval gate before execution |

#### `async execute(subtask: str, state: AgentForgeState) → dict` (abstract)

Subclass implementation. Must return `{output, success, actions_taken}`.

#### `async run(subtask: str, state: AgentForgeState) → dict`

Template method: logs start → approval gate (if destructive) → execute → logs result.

---

### `class TriageAgent(BaseAgent)`

Module: `agentforge.agents.triage_agent`

Destructive agent. Full triage pipeline.

#### `async execute(subtask: str, state: AgentForgeState) → dict`

Steps: fetch issues → classify → log to EvalEngine → approval → apply labels → Notion report → Slack alert → print metrics.

#### `async _classify_issues(issues: list[dict]) → list[dict]`

Batch LLM classification. Returns list of `{issue_number, severity, confidence, reason}`. Falls back to `"low"` severity on LLM failure.

#### `_build_report(issues, classified) → str`

Generates a text report grouped by severity.

#### `_format_slack_alert(classified, notion_url) → str`

Formats a Slack message with severity counts and report link.

---

### `class StandupAgent(BaseAgent)`

Module: `agentforge.agents.standup_agent`

Destructive agent. Daily standup workflow.

#### `async execute(subtask: str, state: AgentForgeState) → dict`

Steps: get username → fetch GitHub events → summarize → LLM generate standup → Notion log → Slack post.

#### `_summarise_events(events: list[dict]) → str`

Converts raw GitHub events into readable activity lines.

#### `async _generate_standup(activity: str, username: str) → Standup`

LLM generates structured standup from activity text. Falls back to error message on failure.

#### `_format_slack_message(standup: Standup, username: str) → str`

Formats standup as a Slack message.

---

### `class DevAgent(BaseAgent)`

Module: `agentforge.agents.dev_agent`

Destructive agent. GitHub operations.

#### `async execute(subtask: str, state: AgentForgeState) → dict`

LLM generates `DevPlan` → dispatches to `create_issue` or `list_issues`.

---

## MCP Servers

### `class BaseMCPServer(ABC)`

Module: `agentforge.mcp.base`

#### `__init__(name: str)`

Initializes logger and circuit breaker.

#### `health_check() → bool` (abstract)

Returns `True` if the server is reachable.

#### `_resilient_get(client, url, **kwargs)`

GET with retry (3x, exp backoff) + circuit breaker. Decorated with `@retry`.

#### `_resilient_post(client, url, **kwargs)`

POST with retry (3x, exp backoff) + circuit breaker. Decorated with `@retry`.

### `class CircuitBreaker`

| Method | Description |
|--------|-------------|
| `call_succeeded()` | Reset failure counter |
| `call_failed()` | Increment failures; open circuit after 3 |
| `is_open() → bool` | Check if circuit is open (auto-resets after 60s) |

---

### `class GitHubMCPServer(BaseMCPServer)`

Module: `agentforge.mcp.github_server`

| Method | Params | Returns |
|--------|--------|---------|
| `create_issue(title, body, owner?, repo?)` | Issue title/body | `{number, url}` |
| `list_issues(state?, owner?, repo?)` | Filter by state | `list[{number, title, body, labels, url}]` |
| `add_labels(issue_number, labels, owner?, repo?)` | Issue # + label list | `bool` |
| `get_user_activity(username, since_hours?)` | GitHub username | `list[{type, repo, created, payload}]` |
| `post_comments(issue_number, body, owner?, repo?)` | Issue # + comment | `dict` (API response) |

### `class NotionMCPServer(BaseMCPServer)`

Module: `agentforge.mcp.notion_server`

| Method | Params | Returns |
|--------|--------|---------|
| `create_page(parent_id, title, content)` | Page details | `{id, url}` |
| `search_page(query)` | Search query | `list[{id, url}]` |

### `class SlackMCPServer(BaseMCPServer)`

Module: `agentforge.mcp.slack_server`

| Method | Params | Returns |
|--------|--------|---------|
| `send_message(channel, text)` | Channel name + message | `{ok, ts}` |
| `list_channels()` | — | `list[{id, name}]` |

---

## EvalEngine

Module: `agentforge.eval_engine`

### `class EvalEngine`

#### `log_triage(issue_number, issue_title, predicted, confidence, run_id, ground_truth?) → TriageEvalRecord`

Appends a prediction record to `~/.agentforge/evals.jsonl`.

#### `compute_metrics(run_id?) → dict`

Returns accuracy, per-label precision/recall. Filters by `run_id` if provided.

```python
# Return format:
{
    'total': int,
    'accuracy': float,
    'per_label': {
        'critical': {'precision': float, 'recall': float},
        'high': {'precision': float, 'recall': float},
        'medium': {'precision': float, 'recall': float},
        'low': {'precision': float, 'recall': float},
    },
    'run_id': str
}
```

#### `print_report(run_id?) → None`

Prints formatted metrics to stdout.

### `TriageEvalRecord` (dataclass)

| Field | Type |
|-------|------|
| `timestamp` | `str` (ISO 8601) |
| `issue_number` | `int` |
| `issue_title` | `str` |
| `predicted` | `SeverityLabel` |
| `ground_truth` | `SeverityLabel \| None` |
| `correct` | `bool \| None` |
| `confidence` | `float` |
| `run_id` | `str` |

---

## Schemas

Module: `agentforge.agents.schemas`

### `DevPlan`

LLM output for DevAgent. Validator: `action` normalized to lowercase.

| Field | Type | Default |
|-------|------|---------|
| `action` | `str` | — |
| `title` | `str` | — |
| `body` | `str` | — |
| `path` | `str` | `""` |

### `TriageItem`

Single classified issue. Validator: `severity` normalized, invalid → `"low"`.

| Field | Type | Default |
|-------|------|---------|
| `issue_number` | `int` | — |
| `severity` | `str` | — |
| `confidence` | `float` | `1.0` |
| `reason` | `str` | `""` |

Valid severities: `critical`, `high`, `medium`, `low`, `wontfix`

### `TriageResponse`

Wrapper for batch classification.

| Field | Type |
|-------|------|
| `items` | `list[TriageItem]` |

### `Standup`

Structured standup output.

| Field | Type |
|-------|------|
| `yesterday` | `str` |
| `today` | `str` |
| `blockers` | `str` |

### `PlanItem`

Single orchestrator subtask.

| Field | Type |
|-------|------|
| `agent` | `str` |
| `subtask` | `str` |
| `confidence` | `float` |
| `parallel` | `bool` |

### `Plan`

Orchestrator decomposition result.

| Field | Type |
|-------|------|
| `items` | `list[PlanItem]` |

---

## Utilities

### `ApprovalGate` (`agentforge.approval`)

#### `async ask(agent_name: str, action: str) → bool`

Shows approval prompt. Returns `True` if `auto_approve` is enabled or user confirms. Returns `False` on rejection or `KeyboardInterrupt`.

### `AgentLogger` (`agentforge.logger`)

#### `__init__(agent_name: str)`

Creates logger with agent-specific color.

| Method | Output |
|--------|--------|
| `info(msg)` | `[AGENT] msg` |
| `success(msg)` | `[AGENT] ✅ msg` (green) |
| `warn(msg)` | `[AGENT] ⚠️ msg` (yellow) |
| `error(msg)` | `[AGENT] ❌ msg` (red) |
| `mcp_call(server, action)` | `[AGENT] → MCP:server action` (dim) |

**Agent Colors:** orchestrator=cyan, dev=magenta, triage=red, standup=white

### `AgentForgeState` (`agentforge.graph.state`)

TypedDict for pipeline state. See [Architecture Guide](architecture.md#state-management).
