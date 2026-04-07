import os 
from pathlib import Path
import logging

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s]: %(message)s'
)

project_name = "agentforge"

## List of files and folders to be created

list_of_files = [
    f"agentforge/__init__.py",
    f"agentforge/cli.py",
    f"agentforge/config.py",
    f"agentforge/logger.py",
    f"agentforge/approval.py",
    f"agentforge/orchestrator.py",
    f"agentforge/eval_engine.py",
    f"agentforge/agents/__init__.py",
    f"agentforge/agents/base.py",
    f"agentforge/agents/research_agent.py",
    f"agentforge/agents/writer_agent.py",
    f"agentforge/agents/dev_agent.py",
    f"agentforge/agents/comms_agent.py",
    f"agentforge/agents/triage_agent.py",
    f"agentforge/agents/standup_agent.py",
    f"agentforge/mcp/__init__.py",
    f"agentforge/mcp/base.py",
    f"agentforge/mcp/github_server.py",
    f"agentforge/mcp/notion_server.py",
    f"agentforge/mcp/slack_server.py",
    f"agentforge/graph/__init__.py",
    f"agentforge/graph/state.py",
    f"agentforge/graph/graph.py",
    f"agentforge/tests/test_mcp_github.py",
    f"agentforge/tests/test_mcp_notion.py",
    f"agentforge/tests/test_agents.py",
    f"agentforge/tests/test_triage_agent.py",
    f"agentforge/tests/test_standup_agent.py",
    f"agentforge/tests/test_eval_engine.py",
    f"pyproject.toml",
    f"README.md",
    f".github/workflows/ci.yml",
]


for filepath in list_of_files:
    filepath = Path(filepath)
    filedir, filename = os.path.split(filepath)

    if filedir != "":
        os.makedirs(filedir, exist_ok=True)
        logging.info(f"Creating directory: {filedir} for file: {filename}")

    if(not filepath.exists()) or (filepath.stat().st_size == 0):
        with open(filepath, "w") as f:
            pass
        logging.info(f"Creating empty file: {filepath}")
    else:
        logging.info(f"{filename} already exists.")