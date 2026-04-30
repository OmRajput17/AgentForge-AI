# 🔥 AgentForge-AI — Multi-Agent Orchestration over MCP

> **Production-grade AI agent platform** that decomposes natural-language tasks into specialized agent workflows — with human-in-the-loop approval, structured LLM output, and full observability.

<p align="center">
  <img src="https://img.shields.io/badge/python-3.11+-blue?style=for-the-badge&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/LangChain-🦜-green?style=for-the-badge" />
  <img src="https://img.shields.io/badge/Pydantic-v2-red?style=for-the-badge" />
  <img src="https://img.shields.io/badge/async-first-purple?style=for-the-badge" />
  <img src="https://img.shields.io/badge/license-MIT-yellow?style=for-the-badge" />
</p>

---

## 🎬 Demo

One command triggers the full pipeline:

```bash
agentforge run "Triage all open bugs and alert the team"
```

**What happens:**
1. 🧠 Orchestrator decomposes the task via LLM
2. 🔍 TriageAgent fetches open GitHub issues
3. ⚡ LLM classifies severity (critical/high/medium/low)
4. 🏷️ Labels applied on GitHub automatically
5. 📝 Notion triage report generated
6. 💬 Slack alert sent to #engineering

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

### Key Components

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

### 1. Install AgentForge

**Option A: Install via PyPI (Recommended)**
```bash
pip install agentforge-ai
```

**Option B: Install from Source**
```bash
git clone https://github.com/OmRajput17/AgentForge-AI.git
cd AgentForge-AI
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux
pip install -e .
```

### 2. Initialize Config

```bash
agentforge init
```

This creates `~/.agentforge/config.yml`. Open it in your editor:

```bash
notepad %USERPROFILE%\.agentforge\config.yml     # Windows
nano ~/.agentforge/config.yml                     # macOS/Linux
```

Full `config.yml`:

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

> **Supports OpenAI and Groq** — switch providers by changing `provider` and `model`. No code changes needed.

### 3. Run a Task

```bash
# Triage bugs — classify, label, report, alert
agentforge run "Triage all open bugs and alert the team"

# Generate daily standup from GitHub activity
agentforge run "Generate daily standup for om"

# Create a GitHub issue via natural language
agentforge run "Create a GitHub issue for the login bug"
```

### 4. Check MCP Server Status

```bash
agentforge server
```

```
  GitHub       ✅ configured
  Notion       ✅ configured
  Slack        ✅ configured
```

---

## 🧪 Running Tests (No API Keys Required)

All tests are fully mocked — they run **without any API keys or network access**.

```bash
# Run the full test suite
pytest agentforge/tests/ -v

# Run specific test modules
pytest agentforge/tests/test_schemas.py -v          # Pydantic schema validation
pytest agentforge/tests/test_triage_agent.py -v     # TriageAgent unit tests
pytest agentforge/tests/test_standup_agent.py -v    # StandupAgent unit tests
pytest agentforge/tests/test_dev_agent.py -v        # DevAgent unit tests
pytest agentforge/tests/test_mcp_github.py -v       # GitHub MCP server tests

# Run with coverage
pytest agentforge/tests/ -v --cov=agentforge --cov-report=term-missing
```

### Test Suite Overview

| Test Module | Tests | What It Covers |
|------------|-------|----------------|
| `test_schemas.py` | 17 | Pydantic validation, severity normalization, wontfix, model_dump |
| `test_triage_agent.py` | 12 | Classification, fallback, report generation, approval gate, Slack alerts |
| `test_standup_agent.py` | 7 | Event summarization, standup generation, full workflow |
| `test_dev_agent.py` | 4 | GitHub issue creation, listing, unknown action, LLM failure |
| `test_mcp_github.py` | — | GitHub API wrapper with mocked HTTP |
| `test_mcp_notion.py` | — | Notion API wrapper |
| `test_mcp_slack.py` | — | Slack API wrapper |
| `test_eval_engine.py` | — | Prediction logging, precision/recall metrics |

---

## 🔒 Production Hardening

### What makes this production-ready:

- **🛡️ Human-in-the-Loop Approval** — Destructive agents (TriageAgent, DevAgent) require explicit user approval before mutating GitHub. Powered by `BaseAgent.run()` → `ApprovalGate.ask()`.

- **📊 Pydantic Structured Output** — No raw `json.loads()` anywhere. All LLM responses go through `with_structured_output(Schema)` with field validators that normalize and sanitize data.

- **🔄 Async-First Architecture** — All blocking MCP calls wrapped in `asyncio.to_thread()`. Orchestrator runs parallel subtasks via `asyncio.gather()`.

- **💥 Graceful Degradation** — Every LLM call has `try/except` with safe fallback responses. Notion/Slack failures are non-fatal. Missing fields handled with `.get()` defaults.

- **🔌 Pluggable LLM Provider** — `get_llm()` factory returns OpenAI or Groq based on config. Switch providers without touching any agent code.

- **📈 EvalEngine Observability** — Every triage prediction is logged to `~/.agentforge/evals.jsonl` with confidence scores. Compute precision/recall per severity label across runs.

- **🔌 Circuit Breaker + Retry** — All MCP servers inherit from `BaseMCPServer` with `tenacity` retry logic and thread-safe circuit breaker for resilient API calls.

---

## 🔄 TriageAgent Workflow

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
├── pyproject.toml
├── requirements.txt
└── README.md
```

---

## 🛠️ Tech Stack

| Technology | Purpose |
|-----------|---------|
| **Python 3.11+** | Core runtime |
| **LangChain** | LLM orchestration with structured output |
| **Groq / OpenAI** | Pluggable LLM providers via `get_llm()` factory |
| **Pydantic v2** | Schema validation, field normalization |
| **asyncio** | Async execution, `to_thread` for blocking MCP calls |
| **httpx** | HTTP client for MCP server API calls |
| **tenacity** | Retry logic + circuit breaker for API resilience |
| **Rich** | Beautiful terminal UI, colored logs, approval prompts |
| **Typer** | CLI framework |
| **pytest + pytest-asyncio** | Async-aware testing |

---

## 📝 License

MIT License — see [LICENSE](LICENSE) for details.

---

<p align="center">
  Built with ❤️ by <a href="https://github.com/OmRajput17">Om Rajput</a>
</p>
