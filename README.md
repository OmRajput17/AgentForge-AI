[![CI](https://github.com/OmRajput17/AgentForge-AI/actions/workflows/ci.yml/badge.svg)](https://github.com/OmRajput17/AgentForge-AI/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/agentforge-ai?style=for-the-badge&logo=pypi&logoColor=white&color=3775A9)](https://pypi.org/project/agentforge-ai/)
[![Python](https://img.shields.io/badge/python-3.11+-blue?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-yellow?style=for-the-badge)](LICENSE)
[![Downloads](https://img.shields.io/pypi/dm/agentforge-ai?style=for-the-badge&logo=pypi&logoColor=white&color=green)](https://pypi.org/project/agentforge-ai/)

<p align="center">
  <img src="https://img.shields.io/badge/LangChain-🦜-green?style=for-the-badge" />
  <img src="https://img.shields.io/badge/Pydantic-v2-red?style=for-the-badge" />
  <img src="https://img.shields.io/badge/async-first-purple?style=for-the-badge" />
</p>

---

# 🔥 AgentForge-AI — Multi-Agent Orchestration over MCP

> **Production-grade AI agent platform** that decomposes natural-language tasks into specialized agent workflows — with human-in-the-loop approval, structured LLM output, and full observability.

AgentForge-AI turns a plain-English task into a coordinated multi-agent pipeline. An LLM-powered orchestrator breaks down your request, routes subtasks to specialized agents (triage, standup, dev), and executes them — with approval gates before any destructive action, structured Pydantic output from every LLM call, and resilient MCP server connections with circuit breakers.

---

## 📑 Table of Contents

- [Demo](#-demo)
- [Key Features](#-key-features)
- [Architecture](#️-architecture)
- [Quick Start](#-quick-start)
- [Configuration](#-configuration)
- [CLI Reference](#-cli-reference)
- [Agent Workflows](#-agent-workflows)
- [MCP Server Layer](#-mcp-server-layer)
- [EvalEngine — Observability](#-evalengine--observability)
- [Testing](#-testing)
- [Project Structure](#-project-structure)
- [Tech Stack](#️-tech-stack)
- [Production Hardening](#-production-hardening)
- [Contributing](#-contributing)
- [License](#-license)

---

## 🎬 Demo

One command triggers the full pipeline:

```bash
agentforge run "Triage all open bugs and alert the team"
```

**What happens under the hood:**

| Step | Action | Detail |
|------|--------|--------|
| 1 | 🧠 **Decompose** | Orchestrator uses LLM to break the task into subtasks |
| 2 | 🔍 **Fetch** | TriageAgent fetches all open GitHub issues via MCP |
| 3 | ⚡ **Classify** | LLM batch-classifies severity (critical / high / medium / low / wontfix) |
| 4 | 📊 **Log** | EvalEngine logs every prediction with confidence scores |
| 5 | ✋ **Approve** | Human-in-the-loop approval before mutating GitHub |
| 6 | 🏷️ **Label** | Severity labels applied to each issue on GitHub |
| 7 | 📝 **Report** | Triage report created as a Notion page |
| 8 | 💬 **Alert** | Slack notification sent to `#engineering` |
| 9 | 📈 **Metrics** | Precision/recall report printed to terminal |

---

## ✨ Key Features

- **🧠 LLM Task Decomposition** — Natural language → structured subtask plan with confidence-based agent routing
- **🛡️ Human-in-the-Loop** — Destructive operations require explicit user approval before execution
- **📊 Structured LLM Output** — All LLM responses go through Pydantic `with_structured_output()` — no raw `json.loads()` anywhere
- **⚡ Async-First** — `asyncio.gather()` for parallel subtasks, `to_thread()` for blocking MCP calls
- **🔌 Pluggable LLM Providers** — Switch between OpenAI and Groq with a single config change
- **🔄 Circuit Breaker + Retry** — All MCP servers inherit resilient `tenacity`-based retry logic
- **📈 EvalEngine** — Every triage prediction logged to JSONL with precision/recall computation
- **💥 Graceful Degradation** — Notion/Slack failures are non-fatal; LLM failures fall back to safe defaults

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────┐
│                    CLI / User                       │
│              "Triage all open bugs"                 │
└──────────────────────┬──────────────────────────────┘
                       │
              ┌────────▼────────┐
              │  Orchestrator   │  LLM decomposes task
              │  (Task Planner) │  into subtasks with
              │                 │  confidence routing
              └───┬────┬────┬───┘
                  │    │    │
         ┌────────┘    │    └────────┐
         ▼             ▼             ▼
   ┌──────────┐  ┌──────────┐  ┌──────────┐
   │ DevAgent │  │ TriageAg │  │ StandupAg│
   │          │  │          │  │          │
   │ GitHub   │  │ Classify │  │ Activity │
   │ Issues   │  │ + Label  │  │ Summary  │
   └────┬─────┘  └────┬─────┘  └────┬─────┘
        │              │              │
        ▼              ▼              ▼
   ┌──────────────────────────────────────┐
   │          MCP Server Layer            │
   │  GitHub  │  Notion  │  Slack         │
   │  (REST)  │  (REST)  │  (REST)        │
   └──────────────────────────────────────┘
```

### Component Overview

| Component | Description |
|-----------|-------------|
| **Orchestrator** | LLM-powered task decomposer with confidence-based routing and keyword fallback |
| **BaseAgent** | Abstract base with approval gates for destructive operations |
| **TriageAgent** | Fetches GitHub issues → LLM classifies severity → labels on GitHub → Notion report → Slack alert |
| **StandupAgent** | Fetches GitHub activity → LLM generates standup → posts to Notion + Slack |
| **DevAgent** | Creates issues, lists repos via GitHub API |
| **EvalEngine** | Logs predictions to JSONL, computes precision/recall per severity label |
| **MCP Servers** | GitHub, Notion, Slack — all with circuit breaker + retry via `tenacity` |

---

## ⚡ Quick Start

### Prerequisites

- **Python 3.11+**
- A **GitHub Personal Access Token** (required)
- **Notion Integration Secret** (optional — for reports)
- **Slack Bot Token** (optional — for alerts)
- An **LLM API key** — [Groq](https://console.groq.com/) (free tier available) or [OpenAI](https://platform.openai.com/)

### 1. Install

**Option A — PyPI (Recommended)**
```bash
pip install agentforge-ai
```

**Option B — From Source**
```bash
git clone https://github.com/OmRajput17/AgentForge-AI.git
cd AgentForge-AI
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS / Linux
pip install -e ".[dev]"        # editable install with dev dependencies
```

### 2. Initialize Configuration

```bash
agentforge init
```

This creates `~/.agentforge/config.yml`. Open it and add your API keys:

```bash
# Windows
notepad %USERPROFILE%\.agentforge\config.yml

# macOS / Linux
nano ~/.agentforge/config.yml
```

### 3. Run Your First Task

```bash
# Triage bugs — classify, label, report, alert
agentforge run "Triage all open bugs and alert the team"

# Generate daily standup from GitHub activity
agentforge run "Generate daily standup for om"

# Create a GitHub issue via natural language
agentforge run "Create a GitHub issue for the login bug"
```

### 4. Check Server Status

```bash
agentforge server
```

```
  GitHub       ✅ configured
  Notion       ✅ configured
  Slack        ✅ configured
```

---

## ⚙️ Configuration

All configuration lives in `~/.agentforge/config.yml`. Run `agentforge init` to generate the default file.

```yaml
# ── LLM Provider ────────────────────────────────────────
llm:
  provider: groq                    # 'openai' or 'groq'
  model: llama-3.3-70b-versatile    # or 'gpt-4o' for OpenAI
  api_key: ''                       # your API key

# ── MCP Server Connections ──────────────────────────────
mcp_servers:
  github_token: ''                  # GitHub PAT (required)
  github_owner: ''                  # GitHub username
  github_repo: ''                   # target repository
  notion_token: ''                  # Notion integration secret (optional)
  notion_page_id: ''                # Notion page ID for reports (optional)
  slack_token: ''                   # Slack bot token (optional)
  slack_channel: general            # Slack channel for alerts

# ── Behavior ────────────────────────────────────────────
auto_approve: false                 # skip approval prompts for destructive ops
confidence_threshold: 0.8           # min confidence for agent routing
max_iterations: 10                  # max subtasks per run
standup_lookback_hours: 24          # how far back to fetch GitHub activity
```

### Configuration Reference

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `llm.provider` | `str` | `openai` | LLM provider — `openai` or `groq` |
| `llm.model` | `str` | `gpt-4o` | Model name matching the chosen provider |
| `llm.api_key` | `str` | `""` | API key for the LLM provider |
| `mcp_servers.github_token` | `str` | `""` | GitHub Personal Access Token (required) |
| `mcp_servers.github_owner` | `str` | `""` | GitHub username / org (default repo owner) |
| `mcp_servers.github_repo` | `str` | `""` | Target repository name |
| `mcp_servers.notion_token` | `str` | `""` | Notion integration secret (optional) |
| `mcp_servers.notion_page_id` | `str` | `""` | Notion page ID for report pages (optional) |
| `mcp_servers.slack_token` | `str` | `""` | Slack bot token with `chat:write` scope (optional) |
| `mcp_servers.slack_channel` | `str` | `general` | Slack channel for alerts (without `#`) |
| `auto_approve` | `bool` | `false` | Skip approval prompts for destructive operations |
| `confidence_threshold` | `float` | `0.8` | Minimum LLM confidence for agent routing (below this triggers keyword fallback) |
| `max_iterations` | `int` | `10` | Maximum number of subtasks per run |
| `standup_lookback_hours` | `int` | `24` | How far back (in hours) to fetch GitHub activity for standup |

> **💡 Tip:** Supports OpenAI and Groq — switch providers by changing `provider` and `model`. No code changes needed.

---

## 💻 CLI Reference

AgentForge provides a `typer`-based CLI with three commands:

### `agentforge init`

Initialize the configuration file at `~/.agentforge/config.yml`.

```bash
agentforge init
```

Creates the config directory and writes the default YAML template. Safe to run multiple times — will not overwrite an existing config.

### `agentforge run <task>`

Run a multi-agent workflow for the given natural-language task.

```bash
agentforge run "Triage all open bugs and alert the team"
agentforge run "Generate daily standup for om"
agentforge run "Create a GitHub issue titled 'Fix login timeout'"
```

The orchestrator decomposes the task via LLM, routes subtasks to agents, and executes them with parallel/sequential scheduling.

### `agentforge server`

Display the connection status of all configured MCP servers.

```bash
agentforge server
```

Shows ✅ or ❌ for each server based on whether its token is configured in `config.yml`.

---

## 🤖 Agent Workflows

### TriageAgent — Bug Triage Pipeline

Fully automated bug triage from issue fetch → classification → labeling → reporting → alerting.

```
  ┌─── Step 1: Fetch ───┐
  │ github.list_issues() │ ← asyncio.to_thread()
  └──────────┬───────────┘
             │
  ┌──────────▼───────────┐
  │ Step 2: Classify     │
  │ LLM batch call       │ ← with_structured_output(TriageResponse)
  │ (all issues at once) │   try/except → fallback to "low"
  └──────────┬───────────┘
             │
  ┌──────────▼───────────┐
  │ Step 3: EvalEngine   │
  │ Log predictions      │ ← confidence scores + run_id
  └──────────┬───────────┘
             │
  ┌──────────▼───────────┐
  │ Step 4: Approval     │
  │ "Label 5 issues?"    │ ← ApprovalGate.ask() — human confirms
  └──────────┬───────────┘
             │
  ┌──────────▼───────────┐
  │ Step 5: Apply Labels │
  │ github.add_labels()  │ ← asyncio.to_thread(), per-issue resilience
  └──────────┬───────────┘
             │
  ┌──────────▼───────────┐
  │ Step 6: Notion       │
  │ Create triage report │ ← Full severity breakdown (non-fatal)
  └──────────┬───────────┘
             │
  ┌──────────▼───────────┐
  │ Step 7: Slack        │
  │ Alert #engineering   │ ← Critical/High/Medium/Low counts (non-fatal)
  └──────────┬───────────┘
             │
  ┌──────────▼───────────┐
  │ Step 8: Eval Report  │
  │ Print metrics        │ ← Accuracy, precision, recall per label
  └──────────────────────┘
```

**Severity Levels:**

| Severity | Criteria |
|----------|----------|
| `critical` | Production down, data loss, security breach |
| `high` | Major functionality broken, no workaround |
| `medium` | Important feature impaired, workaround exists |
| `low` | Cosmetic, typo, minor UX issue |
| `wontfix` | Duplicate, invalid, not a bug |

### StandupAgent — Daily Standup Generator

Generates a formatted daily standup from real GitHub activity.

1. **Fetch** — Reads GitHub events (commits, PRs, issue comments) for the last N hours
2. **Summarize** — Converts raw events into human-readable activity lines
3. **Generate** — LLM formats activity as structured `Yesterday / Today / Blockers`
4. **Log** — Creates a Notion page with the standup content
5. **Post** — Sends the standup to the configured Slack channel

### DevAgent — GitHub Operations

Handles GitHub CRUD operations through natural language.

| Action | Description |
|--------|-------------|
| `create_issue` | Creates a new GitHub issue with LLM-generated title/body |
| `list_issues` | Lists open issues in the configured repository |

All DevAgent operations are **destructive** and require user approval.

---

## 🔌 MCP Server Layer

MCP (Model Context Protocol) servers wrap external REST APIs with built-in resilience patterns.

### BaseMCPServer

All MCP servers inherit from `BaseMCPServer`, which provides:

- **Retry Logic** — 3 attempts with exponential backoff (2s → 4s → 10s) via `tenacity`
- **Circuit Breaker** — Opens after 3 consecutive failures, auto-resets after 60s cooldown
- **Structured Logging** — Every API call is logged with agent-colored Rich output

### Available Servers

| Server | API | Methods |
|--------|-----|---------|
| **GitHubMCPServer** | GitHub REST API v3 | `create_issue()`, `list_issues()`, `add_labels()`, `get_user_activity()`, `post_comments()` |
| **NotionMCPServer** | Notion API v1 | `create_page()`, `search_page()` |
| **SlackMCPServer** | Slack Web API | `send_message()`, `list_channels()` |

### Resilience Pattern

```python
# Every HTTP call goes through this pattern:
BaseMCPServer._resilient_get(client, url)
#  → Check circuit breaker (skip if open)
#  → Make HTTP request via httpx
#  → On success: reset circuit breaker
#  → On failure: increment failure count → retry up to 3x
#  → After 3 failures: circuit opens for 60s
```

---

## 📈 EvalEngine — Observability

The EvalEngine provides a lightweight ML-ops layer for tracking triage quality over time.

### How It Works

1. **Log** — Every triage prediction is appended to `~/.agentforge/evals.jsonl`
2. **Measure** — Compute accuracy, precision, and recall per severity label
3. **Report** — Print a formatted metrics report to the terminal

### JSONL Record Format

```json
{
  "timestamp": "2026-05-10T13:15:00+00:00",
  "issue_number": 42,
  "issue_title": "Login page crashes on mobile",
  "predicted": "critical",
  "ground_truth": null,
  "correct": null,
  "confidence": 0.92,
  "run_id": "a1b2c3d4"
}
```

### Programmatic Usage

```python
from agentforge.eval_engine import EvalEngine

engine = EvalEngine()

# Log a prediction
engine.log_triage(
    issue_number=42,
    issue_title="Login crash",
    predicted="critical",
    confidence=0.92,
    run_id="a1b2c3d4",
    ground_truth="critical"  # optional
)

# Compute metrics (all runs or specific run)
metrics = engine.compute_metrics(run_id="a1b2c3d4")
# {'total': 10, 'accuracy': 0.8, 'per_label': {...}, 'run_id': 'a1b2c3d4'}

# Print formatted report
engine.print_report()
```

---

## 🧪 Testing

All tests are **fully mocked** — they run without any API keys or network access.

### Run the Full Suite

```bash
# All tests
pytest agentforge/tests/ -v

# With coverage report
pytest agentforge/tests/ -v --cov=agentforge --cov-report=term-missing

# Specific module
pytest agentforge/tests/test_triage_agent.py -v
```

### Test Suite Overview

| Test Module | What It Covers |
|------------|----------------|
| `test_schemas.py` | Pydantic validation, severity normalization, wontfix handling, model_dump |
| `test_triage_agent.py` | Classification, fallback, report generation, approval gate, Slack alerts |
| `test_standup_agent.py` | Event summarization, standup generation, full workflow |
| `test_dev_agent.py` | GitHub issue creation, listing, unknown action, LLM failure |
| `test_mcp_github.py` | GitHub API wrapper with mocked HTTP requests |
| `test_mcp_notion.py` | Notion API wrapper with mocked HTTP |
| `test_mcp_slack.py` | Slack API wrapper with mocked HTTP |
| `test_mcp_base.py` | Circuit breaker logic, retry behavior |
| `test_eval_engine.py` | Prediction logging, precision/recall metrics |
| `test_orchestrator.py` | Task decomposition, parallel/sequential execution |
| `test_config.py` | Config loading, LLM factory, default values |
| `test_approval.py` | Approval gate, auto-approve mode |
| `test_agents_base.py` | BaseAgent ABC contract, destructive flag |
| `test_logger.py` | Agent-colored logging output |

### CI Pipeline

Tests run automatically on every push/PR to `main` via GitHub Actions across Python 3.11 and 3.12.

---

## 📁 Project Structure

```
AgentForge/
├── agentforge/
│   ├── agents/
│   │   ├── base.py              # BaseAgent ABC — approval gates, logging
│   │   ├── dev_agent.py         # GitHub operations agent
│   │   ├── triage_agent.py      # Bug triage workflow agent
│   │   ├── standup_agent.py     # Daily standup generator
│   │   └── schemas.py           # Pydantic models for structured LLM output
│   ├── mcp/
│   │   ├── base.py              # BaseMCPServer — circuit breaker + retry
│   │   ├── github_server.py     # GitHub REST API wrapper
│   │   ├── notion_server.py     # Notion API wrapper
│   │   └── slack_server.py      # Slack API wrapper
│   ├── graph/
│   │   └── state.py             # AgentForgeState TypedDict
│   ├── tests/                   # Full test suite (all mocked, no API keys needed)
│   ├── orchestrator.py          # LLM task decomposer + parallel execution
│   ├── eval_engine.py           # Prediction logging + precision/recall
│   ├── approval.py              # Human-in-the-loop approval gate
│   ├── config.py                # YAML config + LLM factory + Pydantic settings
│   ├── logger.py                # Rich console logger with agent colors
│   └── cli.py                   # Typer CLI entrypoint
├── .github/
│   └── workflows/
│       ├── ci.yml               # CI pipeline (test on Python 3.11 + 3.12)
│       └── publish.yml          # Auto-publish to PyPI on version tags
├── docs/                        # Extended documentation
│   ├── architecture.md          # System design deep dive
│   ├── api-reference.md         # Full API reference
│   └── configuration.md         # Configuration guide
├── pyproject.toml               # PEP 621 project metadata
├── requirements.txt             # Pinned dependencies
├── CONTRIBUTING.md              # Contribution guidelines
├── CHANGELOG.md                 # Version history
├── SECURITY.md                  # Security policy
├── LICENSE                      # MIT License
└── README.md                    # This file
```

---

## 🛠️ Tech Stack

| Technology | Purpose |
|-----------|---------|
| **Python 3.11+** | Core runtime with modern typing (`str \| None`, `list[dict]`) |
| **LangChain** | LLM orchestration with `with_structured_output()` |
| **Groq / OpenAI** | Pluggable LLM providers via `get_llm()` factory |
| **Pydantic v2** | Schema validation, field normalization, settings management |
| **asyncio** | Async execution, `to_thread()` for blocking MCP calls, `gather()` for parallelism |
| **httpx** | Modern HTTP client for all MCP server API calls |
| **tenacity** | Retry logic with exponential backoff for API resilience |
| **Rich** | Beautiful terminal UI — colored logs, panels, approval prompts |
| **Typer** | CLI framework with auto-generated help |
| **pytest + pytest-asyncio** | Async-aware testing with full coverage |

---

## 🔒 Production Hardening

### What makes this production-ready:

- **🛡️ Human-in-the-Loop Approval** — Destructive agents (TriageAgent, DevAgent) require explicit user approval before mutating GitHub. Powered by `BaseAgent.run()` → `ApprovalGate.ask()`.

- **📊 Pydantic Structured Output** — No raw `json.loads()` anywhere. All LLM responses go through `with_structured_output(Schema)` with field validators that normalize and sanitize data.

- **🔄 Async-First Architecture** — All blocking MCP calls wrapped in `asyncio.to_thread()`. Orchestrator runs parallel subtasks via `asyncio.gather()`.

- **💥 Graceful Degradation** — Every LLM call has `try/except` with safe fallback responses. Notion/Slack failures are non-fatal. Missing fields handled with `.get()` defaults.

- **🔌 Pluggable LLM Provider** — `get_llm()` factory returns OpenAI or Groq based on config. Switch providers without touching any agent code.

- **📈 EvalEngine Observability** — Every triage prediction is logged to `~/.agentforge/evals.jsonl` with confidence scores. Compute precision/recall per severity label across runs.

- **🔌 Circuit Breaker + Retry** — All MCP servers inherit from `BaseMCPServer` with `tenacity` retry logic (3 attempts, exponential backoff) and thread-safe circuit breaker (auto-reset after 60s).

- **🔑 Confidence-Based Routing** — Orchestrator scores routing confidence per subtask. Low-confidence assignments fall back to keyword matching, ensuring reliable agent selection.

---

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on:

- Setting up your development environment
- Running the test suite
- Submitting pull requests
- Code style and conventions

---

## 📝 License

MIT License — see [LICENSE](LICENSE) for details.

---

## 🔗 Links

- **PyPI:** [https://pypi.org/project/agentforge-ai/](https://pypi.org/project/agentforge-ai/)
- **GitHub:** [https://github.com/OmRajput17/AgentForge-AI](https://github.com/OmRajput17/AgentForge-AI)
- **Issues:** [https://github.com/OmRajput17/AgentForge-AI/issues](https://github.com/OmRajput17/AgentForge-AI/issues)

---

<p align="center">
  Built with ❤️ by <a href="https://github.com/OmRajput17">Om Rajput</a>
</p>
