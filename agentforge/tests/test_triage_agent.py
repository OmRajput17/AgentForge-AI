# agentforge/tests/test_triage_agent.py
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from agentforge.agents.triage_agent import TriageAgent
from agentforge.agents.schemas import TriageItem, TriageResponse


# ═══════════════════════════════════════════════════════════════════
# TriageAgent._classify_issues  — async unit tests
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
@patch('agentforge.agents.triage_agent.ChatOpenAI')
class TestClassifyIssues:

    async def test_happy_path(self, mock_llm_cls):
        agent = TriageAgent()
        mock_structured = MagicMock()
        mock_structured.ainvoke = AsyncMock(
            return_value=TriageResponse(items=[
                TriageItem(issue_number=1, severity='high', reason='broken'),
            ])
        )
        agent._llm = MagicMock()
        agent._llm.with_structured_output.return_value = mock_structured

        issues = [{"number": 1, "title": "Bug", "body": "It's broken"}]
        result = await agent._classify_issues(issues)

        assert len(result) == 1
        assert result[0]["severity"] == "high"
        assert result[0]["issue_number"] == 1

    async def test_llm_exception_returns_empty(self, mock_llm_cls):
        """LLM raises an exception — should return [] gracefully."""
        agent = TriageAgent()
        mock_structured = MagicMock()
        mock_structured.ainvoke = AsyncMock(side_effect=ValueError("parse error"))
        agent._llm = MagicMock()
        agent._llm.with_structured_output.return_value = mock_structured

        issues = [{"number": 1, "title": "Bug", "body": "body"}]
        result = await agent._classify_issues(issues)

        assert result == []

    async def test_severity_normalized(self, mock_llm_cls):
        """Invalid severity in LLM output should be normalized to 'low'."""
        agent = TriageAgent()
        mock_structured = MagicMock()
        mock_structured.ainvoke = AsyncMock(
            return_value=TriageResponse(items=[
                TriageItem(issue_number=1, severity='URGENT', reason='bad'),
            ])
        )
        agent._llm = MagicMock()
        agent._llm.with_structured_output.return_value = mock_structured

        issues = [{"number": 1, "title": "Bug", "body": "body"}]
        result = await agent._classify_issues(issues)

        assert len(result) == 1
        assert result[0]["severity"] == "low"

    async def test_multiple_items(self, mock_llm_cls):
        agent = TriageAgent()
        mock_structured = MagicMock()
        mock_structured.ainvoke = AsyncMock(
            return_value=TriageResponse(items=[
                TriageItem(issue_number=1, severity='critical', reason='data loss'),
                TriageItem(issue_number=2, severity='medium', reason='perf'),
            ])
        )
        agent._llm = MagicMock()
        agent._llm.with_structured_output.return_value = mock_structured

        issues = [
            {"number": 1, "title": "A", "body": ""},
            {"number": 2, "title": "B", "body": ""},
        ]
        result = await agent._classify_issues(issues)

        assert len(result) == 2
        assert result[0]["severity"] == "critical"
        assert result[1]["severity"] == "medium"


# ═══════════════════════════════════════════════════════════════════
# TriageAgent._build_report  — async unit tests
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
@patch('agentforge.agents.triage_agent.ChatOpenAI')
class TestBuildReport:

    async def test_report_contains_all_severities(self, mock_llm_cls):
        agent = TriageAgent()
        issues = [
            {"number": 1, "title": "Critical bug", "url": "https://github.com/issues/1"},
            {"number": 2, "title": "Minor typo", "url": "https://github.com/issues/2"},
        ]
        classified = [
            {"issue_number": 1, "severity": "critical", "reason": "data loss"},
            {"issue_number": 2, "severity": "low", "reason": "cosmetic"},
        ]
        report = agent._build_report(issues, classified)

        assert "Bug Triage Report" in report
        assert "CRITICAL (1)" in report
        assert "LOW (1)" in report
        assert "#1" in report
        assert "#2" in report

    async def test_report_with_no_classified(self, mock_llm_cls):
        """Unclassified issues default to 'low' in the report."""
        agent = TriageAgent()
        issues = [{"number": 1, "title": "Something", "url": "https://github.com/issues/1"}]
        classified = []
        report = agent._build_report(issues, classified)

        assert "LOW (1)" in report


# ═══════════════════════════════════════════════════════════════════
# TriageAgent.execute  — full workflow integration tests
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
@patch('agentforge.agents.triage_agent.get_settings')
@patch('agentforge.agents.triage_agent.ChatOpenAI')
class TestTriageExecute:

    def _make_agent(self):
        agent = TriageAgent()
        agent._github = MagicMock()
        agent._notion = MagicMock()
        agent._slack = MagicMock()
        return agent

    def _mock_settings(self, mock_get_settings, notion_token='', slack_token=''):
        settings = MagicMock()
        settings.llm.model = 'gpt-4o'
        settings.mcp_servers.notion_token = notion_token
        settings.mcp_servers.slack_token = slack_token
        mock_get_settings.return_value = settings

    def _mock_structured_llm(self, agent, triage_response):
        """Helper: make agent._llm.with_structured_output().ainvoke() return the given response."""
        mock_structured = MagicMock()
        mock_structured.ainvoke = AsyncMock(return_value=triage_response)
        agent._llm = MagicMock()
        agent._llm.with_structured_output.return_value = mock_structured

    async def test_no_open_issues(self, mock_llm_cls, mock_get_settings):
        self._mock_settings(mock_get_settings)
        agent = self._make_agent()
        agent._github.list_issues.return_value = []

        result = await agent.execute('triage', {})

        assert result['success'] is True
        assert 'No open issues' in result['output']

    async def test_github_fetch_failure(self, mock_llm_cls, mock_get_settings):
        self._mock_settings(mock_get_settings)
        agent = self._make_agent()
        agent._github.list_issues.side_effect = ConnectionError('GitHub is down')

        result = await agent.execute('triage', {})

        assert result['success'] is False
        assert 'Failed to fetch issues' in result['output']

    async def test_happy_path_labels_applied(self, mock_llm_cls, mock_get_settings):
        self._mock_settings(mock_get_settings)
        agent = self._make_agent()
        agent._github.list_issues.return_value = [
            {"number": 1, "title": "Bug A", "body": "broken"},
            {"number": 2, "title": "Bug B", "body": "slow"},
        ]

        self._mock_structured_llm(agent, TriageResponse(items=[
            TriageItem(issue_number=1, severity='critical', reason='data loss'),
            TriageItem(issue_number=2, severity='medium', reason='perf'),
        ]))

        result = await agent.execute('triage', {})

        assert result['success'] is True
        assert 'Bug Triage Report' in result['output']
        assert any('Labeled #1' in a for a in result['actions_taken'])
        assert any('Labeled #2' in a for a in result['actions_taken'])
        # Verify add_labels was actually called
        assert agent._github.add_labels.call_count == 2

    async def test_classification_failure_still_succeeds(self, mock_llm_cls, mock_get_settings):
        """If LLM classification fails, execute still succeeds with an empty report."""
        self._mock_settings(mock_get_settings)
        agent = self._make_agent()
        agent._github.list_issues.return_value = [
            {"number": 1, "title": "Bug", "body": "body"},
        ]

        # Structured LLM raises — _classify_issues returns []
        mock_structured = MagicMock()
        mock_structured.ainvoke = AsyncMock(side_effect=ValueError("LLM error"))
        agent._llm = MagicMock()
        agent._llm.with_structured_output.return_value = mock_structured

        result = await agent.execute('triage', {})

        assert result['success'] is True
        # No labels should have been added
        agent._github.add_labels.assert_not_called()

    async def test_label_failure_is_resilient(self, mock_llm_cls, mock_get_settings):
        """If add_labels fails for one issue, the rest still proceed."""
        self._mock_settings(mock_get_settings)
        agent = self._make_agent()
        agent._github.list_issues.return_value = [
            {"number": 1, "title": "A", "body": ""},
            {"number": 2, "title": "B", "body": ""},
        ]

        self._mock_structured_llm(agent, TriageResponse(items=[
            TriageItem(issue_number=1, severity='high', reason=''),
            TriageItem(issue_number=2, severity='low', reason=''),
        ]))

        # First call fails, second succeeds
        call_count = {'n': 0}
        def add_labels_effect(*args, **kwargs):
            call_count['n'] += 1
            if call_count['n'] == 1:
                raise RuntimeError('API error')
            return None
        agent._github.add_labels.side_effect = add_labels_effect

        result = await agent.execute('triage', {})

        assert result['success'] is True
        assert agent._github.add_labels.call_count == 2
        # Only the second label should be in actions
        assert any('Labeled #2' in a for a in result['actions_taken'])
        assert not any('Labeled #1' in a for a in result['actions_taken'])

    async def test_slack_and_notion_called_when_configured(self, mock_llm_cls, mock_get_settings):
        self._mock_settings(mock_get_settings, notion_token='tok_notion', slack_token='tok_slack')
        agent = self._make_agent()
        agent._github.list_issues.return_value = [
            {"number": 1, "title": "Bug", "body": ""},
        ]
        agent._notion.create_page.return_value = {"url": "https://notion.so/page"}

        self._mock_structured_llm(agent, TriageResponse(items=[
            TriageItem(issue_number=1, severity='high', reason='bad'),
        ]))

        result = await agent.execute('triage', {})

        assert result['success'] is True
        agent._notion.create_page.assert_called_once()
        agent._slack.send_message.assert_called_once()
        assert any('Notion' in a for a in result['actions_taken'])
        assert any('Slack' in a for a in result['actions_taken'])
