# agentforge/tests/test_standup_agent.py
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from agentforge.agents.standup_agent import StandupAgent
from agentforge.agents.schemas import Standup


def _mock_settings(mock_get_settings, notion_token='', slack_token='', github_owner='testuser'):
    settings = MagicMock()
    settings.llm.model = 'gpt-4o'
    settings.mcp_servers.notion_token = notion_token
    settings.mcp_servers.slack_token = slack_token
    settings.mcp_servers.github_owner = github_owner
    mock_get_settings.return_value = settings


# ═══════════════════════════════════════════════════════════════════
# StandupAgent._summarise_events
# ═══════════════════════════════════════════════════════════════════

@patch('agentforge.agents.standup_agent.ChatOpenAI')
@patch('agentforge.agents.standup_agent.get_settings')
class TestSummariseEvents:

    def test_push_event(self, mock_settings, mock_llm):
        _mock_settings(mock_settings)
        agent = StandupAgent()
        events = [{
            'type': 'PushEvent',
            'repo': 'owner/repo',
            'payload': {'commits': [{'message': 'fix bug'}]}
        }]
        result = agent._summarise_events(events)
        assert 'Pushed: fix bug' in result

    def test_pr_event(self, mock_settings, mock_llm):
        _mock_settings(mock_settings)
        agent = StandupAgent()
        events = [{
            'type': 'PullRequestEvent',
            'repo': 'owner/repo',
            'payload': {'action': 'opened', 'pull_request': {'title': 'Add feature'}}
        }]
        result = agent._summarise_events(events)
        assert 'PR opened' in result

    def test_no_events(self, mock_settings, mock_llm):
        _mock_settings(mock_settings)
        agent = StandupAgent()
        result = agent._summarise_events([])
        assert 'No Github activity' in result


# ═══════════════════════════════════════════════════════════════════
# StandupAgent._generate_standup
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
@patch('agentforge.agents.standup_agent.ChatOpenAI')
@patch('agentforge.agents.standup_agent.get_settings')
class TestGenerateStandup:

    async def test_happy_path(self, mock_settings, mock_llm_cls):
        _mock_settings(mock_settings)
        agent = StandupAgent()

        mock_structured = MagicMock()
        mock_structured.ainvoke = AsyncMock(
            return_value=Standup(yesterday='Fixed bugs', today='Write tests', blockers='None')
        )
        agent._llm = MagicMock()
        agent._llm.with_structured_output.return_value = mock_structured

        result = await agent._generate_standup('some activity', 'testuser')

        assert isinstance(result, Standup)
        assert result.yesterday == 'Fixed bugs'
        assert result.today == 'Write tests'
        assert result.blockers == 'None'

    async def test_llm_failure_returns_fallback(self, mock_settings, mock_llm_cls):
        _mock_settings(mock_settings)
        agent = StandupAgent()

        mock_structured = MagicMock()
        mock_structured.ainvoke = AsyncMock(side_effect=ValueError("bad output"))
        agent._llm = MagicMock()
        agent._llm.with_structured_output.return_value = mock_structured

        result = await agent._generate_standup('some activity', 'testuser')

        assert isinstance(result, Standup)
        assert 'LLM error' in result.yesterday


# ═══════════════════════════════════════════════════════════════════
# StandupAgent.execute  — full workflow
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
@patch('agentforge.agents.standup_agent.ChatOpenAI')
@patch('agentforge.agents.standup_agent.get_settings')
class TestStandupExecute:

    def _make_agent(self):
        agent = StandupAgent()
        agent._github = MagicMock()
        agent._slack = MagicMock()
        agent._notion = MagicMock()
        return agent

    async def test_full_workflow(self, mock_settings, mock_llm_cls):
        _mock_settings(mock_settings, notion_token='tok', slack_token='tok')
        agent = self._make_agent()

        agent._github.get_user_activity.return_value = [{
            'type': 'PushEvent',
            'repo': 'owner/repo',
            'payload': {'commits': [{'message': 'fix'}]}
        }]
        agent._notion.create_page.return_value = {'url': 'https://notion.so/page'}

        mock_structured = MagicMock()
        mock_structured.ainvoke = AsyncMock(
            return_value=Standup(yesterday='Fixed bugs', today='Tests', blockers='None')
        )
        agent._llm = MagicMock()
        agent._llm.with_structured_output.return_value = mock_structured

        result = await agent.execute('standup', {})

        assert result['success'] is True
        assert 'Fixed bugs' in result['output']
        agent._notion.create_page.assert_called_once()
        agent._slack.send_message.assert_called_once()

    async def test_no_notion_or_slack(self, mock_settings, mock_llm_cls):
        """When tokens are empty, Notion/Slack should be skipped."""
        _mock_settings(mock_settings, notion_token='', slack_token='')
        agent = self._make_agent()

        agent._github.get_user_activity.return_value = []

        mock_structured = MagicMock()
        mock_structured.ainvoke = AsyncMock(
            return_value=Standup(yesterday='Nothing', today='Plan', blockers='None')
        )
        agent._llm = MagicMock()
        agent._llm.with_structured_output.return_value = mock_structured

        result = await agent.execute('standup', {})

        assert result['success'] is True
        agent._notion.create_page.assert_not_called()
        agent._slack.send_message.assert_not_called()
