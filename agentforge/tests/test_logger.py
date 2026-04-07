# Save as: agentforge/tests/test_logger.py
import pytest
from agentforge.logger import AgentLogger, AGENT_COLORS

class TestAgentLogger:
    def test_logger_creation(self):
        log = AgentLogger("research")
        assert log.name == "research"
        assert log.color == "bold green"

    def test_logger_unknown_agent(self):
        log = AgentLogger("unknown_agent")
        assert log.color == "white"  # default fallback

    def test_all_agent_colors_defined(self):
        expected = ['orchestrator', 'research', 'writer', 'dev', 'comms', 'triage', 'standup']
        for agent in expected:
            assert agent in AGENT_COLORS

    def test_methods_exist(self):
        log = AgentLogger("dev")
        assert callable(log.info)
        assert callable(log.success)
        assert callable(log.warn)
        assert callable(log.error)
        assert callable(log.mcp_call)
