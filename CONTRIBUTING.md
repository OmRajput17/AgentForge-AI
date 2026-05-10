# Contributing to AgentForge-AI

Thank you for your interest in contributing to AgentForge-AI! This document provides guidelines and instructions for contributing.

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Project Architecture](#project-architecture)
- [Making Changes](#making-changes)
- [Testing](#testing)
- [Pull Request Process](#pull-request-process)
- [Code Style](#code-style)
- [Adding a New Agent](#adding-a-new-agent)
- [Adding a New MCP Server](#adding-a-new-mcp-server)

---

## Code of Conduct

By participating in this project, you agree to maintain a respectful and inclusive environment. Be kind, constructive, and professional in all interactions.

---

## Getting Started

1. **Fork** the repository on GitHub
2. **Clone** your fork locally
3. **Create a branch** for your changes
4. **Make your changes** with tests
5. **Submit a pull request**

---

## Development Setup

### Prerequisites

- Python 3.11 or higher
- Git

### Setup

```bash
# Clone your fork
git clone https://github.com/<your-username>/AgentForge-AI.git
cd AgentForge-AI

# Create a virtual environment
python -m venv venv

# Activate it
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS / Linux

# Install in development mode with dev dependencies
pip install -e ".[dev]"

# Verify the install
agentforge --help
```

### Verify Everything Works

```bash
# Run the full test suite
pytest agentforge/tests/ -v

# Run with coverage
pytest agentforge/tests/ -v --cov=agentforge --cov-report=term-missing
```

---

## Project Architecture

```
agentforge/
├── agents/          # Specialized agents (TriageAgent, StandupAgent, DevAgent)
│   ├── base.py      # BaseAgent ABC — approval gates, logging
│   └── schemas.py   # Pydantic models for structured LLM output
├── mcp/             # MCP server wrappers (GitHub, Notion, Slack)
│   └── base.py      # BaseMCPServer — circuit breaker + retry
├── graph/           # State management
│   └── state.py     # AgentForgeState TypedDict
├── tests/           # Full test suite (all mocked)
├── orchestrator.py  # LLM task decomposer + parallel execution
├── eval_engine.py   # Prediction logging + metrics
├── approval.py      # Human-in-the-loop approval gate
├── config.py        # YAML config + LLM factory
├── logger.py        # Rich console logger
└── cli.py           # Typer CLI entrypoint
```

### Key Design Patterns

| Pattern | Where | Why |
|---------|-------|-----|
| **Abstract Base Classes** | `BaseAgent`, `BaseMCPServer` | Enforce consistent interfaces |
| **Approval Gate** | `BaseAgent.run()` | Human-in-the-loop for destructive ops |
| **Circuit Breaker** | `BaseMCPServer` | Prevent cascading failures |
| **Structured Output** | All LLM calls | Type-safe Pydantic parsing |
| **Keyword Fallback** | `Orchestrator._keyword_route()` | Reliability when LLM confidence is low |
| **Factory Pattern** | `config.get_llm()` | Pluggable LLM providers |

---

## Making Changes

### Branch Naming

Use descriptive branch names:

```
feature/add-jira-mcp-server
fix/triage-agent-empty-issues
docs/update-api-reference
test/add-orchestrator-edge-cases
```

### Commit Messages

Follow conventional commit format:

```
feat: add Jira MCP server integration
fix: handle empty issue body in triage classification
docs: update configuration guide with Slack scopes
test: add edge case for orchestrator keyword fallback
refactor: extract circuit breaker to standalone module
```

---

## Testing

### Running Tests

```bash
# Full suite
pytest agentforge/tests/ -v

# Specific module
pytest agentforge/tests/test_triage_agent.py -v

# With coverage
pytest agentforge/tests/ -v --cov=agentforge --cov-report=term-missing

# Only failed tests from last run
pytest agentforge/tests/ --lf
```

### Writing Tests

All tests must be **fully mocked** — no API keys or network access required.

```python
# Example: Testing a new agent
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

@pytest.mark.asyncio
async def test_my_agent_execute():
    """Test that MyAgent processes subtask correctly."""
    with patch('agentforge.agents.my_agent.get_llm') as mock_llm, \
         patch('agentforge.agents.my_agent.get_settings') as mock_settings:

        # Setup mocks
        mock_settings.return_value = MagicMock(...)

        agent = MyAgent()
        result = await agent.execute("do something", state={...})

        assert result['success'] is True
        assert 'actions_taken' in result
```

### Test Requirements

- Every new feature must include tests
- Every bug fix must include a regression test
- Tests must pass on both Python 3.11 and 3.12
- All tests must be async-compatible (use `@pytest.mark.asyncio`)
- No real API calls — mock everything with `unittest.mock`

---

## Pull Request Process

1. **Ensure all tests pass** locally before submitting
2. **Update documentation** if your change affects the public API
3. **Add tests** for any new functionality
4. **Keep PRs focused** — one feature or fix per PR
5. **Fill out the PR template** with a clear description

### PR Checklist

- [ ] Tests pass locally (`pytest agentforge/tests/ -v`)
- [ ] New code has test coverage
- [ ] Documentation updated (if applicable)
- [ ] No breaking changes (or documented in PR description)
- [ ] Code follows project style conventions

---

## Code Style

### General Guidelines

- **Type hints** everywhere — use Python 3.11+ syntax (`str | None`, `list[dict]`)
- **Docstrings** for all public classes and methods
- **No raw `json.loads()`** — use Pydantic `with_structured_output()` for LLM responses
- **Async-first** — use `asyncio.to_thread()` for blocking calls
- **Graceful degradation** — wrap external calls in `try/except` with fallbacks

### Formatting

- Use consistent indentation (4 spaces)
- Keep line length reasonable (~100 characters)
- Use `f-strings` for string formatting
- Import order: stdlib → third-party → local

### Example

```python
import asyncio                              # stdlib
from langchain_core.messages import HumanMessage  # third-party
from agentforge.agents.base import BaseAgent      # local

class MyAgent(BaseAgent):
    """Handles a specific workflow with full observability."""

    def __init__(self):
        super().__init__('my_agent', destructive=False)

    async def execute(self, subtask: str, state: AgentForgeState) -> dict:
        """Execute the subtask and return structured results."""
        try:
            result = await asyncio.to_thread(self._do_work, subtask)
            return {'output': result, 'success': True, 'actions_taken': [...]}
        except Exception as e:
            self.logger.error(f'Failed: {e}')
            return {'output': f'Error: {e}', 'success': False, 'actions_taken': []}
```

---

## Adding a New Agent

1. **Create the agent** in `agentforge/agents/`:

```python
# agentforge/agents/my_agent.py
from agentforge.agents.base import BaseAgent
from agentforge.graph.state import AgentForgeState

class MyAgent(BaseAgent):
    """Description of what this agent does."""

    def __init__(self):
        super().__init__('my_agent', destructive=False)

    async def execute(self, subtask: str, state: AgentForgeState) -> dict:
        # Your implementation
        return {'output': '...', 'success': True, 'actions_taken': [...]}
```

2. **Add Pydantic schema** (if the agent uses LLM) in `agentforge/agents/schemas.py`

3. **Register the agent** in `agentforge/orchestrator.py`:

```python
AGENT_REGISTRY = {
    "dev": DevAgent,
    "triage": TriageAgent,
    "standup": StandupAgent,
    "my_agent": MyAgent,        # ← Add here
}
```

4. **Add keyword mappings** for fallback routing:

```python
KEYWORD_MAPPING = {
    ...
    'my_agent': ['keyword1', 'keyword2'],  # ← Add here
}
```

5. **Write tests** in `agentforge/tests/test_my_agent.py`

6. **Update documentation**

---

## Adding a New MCP Server

1. **Create the server** in `agentforge/mcp/`:

```python
# agentforge/mcp/my_server.py
import httpx
from agentforge.mcp.base import BaseMCPServer
from agentforge.config import get_settings

class MyMCPServer(BaseMCPServer):
    """Wraps the My Service REST API."""
    BASE = 'https://api.myservice.com/v1'

    def __init__(self):
        super().__init__('my_service')
        token = get_settings().mcp_servers.my_token
        self._headers = {'Authorization': f'Bearer {token}'}
        self._client = httpx.Client(timeout=5.0)

    def health_check(self) -> bool:
        try:
            r = self._resilient_get(self._client, f'{self.BASE}/me', headers=self._headers)
            return r.status_code == 200
        except Exception:
            return False

    def my_method(self, param: str) -> dict:
        self._log_call(f'my_method → {param}')
        r = self._resilient_get(self._client, f'{self.BASE}/resource', headers=self._headers)
        r.raise_for_status()
        return r.json()
```

2. **Add config fields** in `agentforge/config.py`:

```python
class MCPServerConfig(BaseModel):
    ...
    my_token: str = ""  # ← Add here
```

3. **Add to CLI server status** in `agentforge/cli.py`

4. **Write tests** in `agentforge/tests/test_mcp_my_server.py`

---

## Questions?

If you have questions about contributing, feel free to [open an issue](https://github.com/OmRajput17/AgentForge-AI/issues) or start a discussion.

Thank you for helping make AgentForge-AI better! 🔥
