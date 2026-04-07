# Save as: agentforge/tests/test_config.py
import pytest
from unittest.mock import patch, mock_open
from agentforge.config import Settings, LLMConfig, MCPServerConfig, get_settings, init_config

class TestSettings:
    def test_default_settings(self):
        s = Settings()
        assert s.llm.provider == "openai"
        assert s.llm.model == "gpt-4o"
        assert s.auto_approve is False
        assert s.confidence_threshold == 0.8
        assert s.max_iterations == 10

    def test_llm_config_defaults(self):
        llm = LLMConfig()
        assert llm.provider == "openai"
        assert llm.model == "gpt-4o"
        assert llm.api_key == ""

    def test_mcp_server_config_defaults(self):
        mcp = MCPServerConfig()
        assert mcp.github_token == ""
        assert mcp.notion_token == ""
        assert mcp.slack_token == ""
        assert mcp.tavily_api == ""

    def test_settings_with_custom_values(self):
        s = Settings(
            llm=LLMConfig(provider="groq", model="llama3", api_key="test-key"),
            auto_approve=True,
            confidence_threshold=0.9,
            max_iterations=5,
        )
        assert s.llm.provider == "groq"
        assert s.auto_approve is True
        assert s.confidence_threshold == 0.9
