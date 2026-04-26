# agentforge/tests/test_triage_agent.py
"""
Unit tests for TriageAgent — classify, report, slack, and full execute workflow.
All tests mock ChatOpenAI + get_settings so they run without API keys.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from agentforge.agents.triage_agent import TriageAgent
from agentforge.agents.schemas import TriageItem, TriageResponse
from agentforge.graph.state import AgentForgeState

SAMPLE_STATE: AgentForgeState = {
    'task': 'triage', 'subtasks': [], 'results': [], 'current_agent': '',
    'iteration': 0, 'completed': False, 'audit_log': []
}

SAMPLE_ISSUES = [
    {'number': 1, 'title': 'App crashes on login', 'body': 'Users cannot log in', 'labels': [], 'url': 'https://github.com/repo/issues/1'},
    {'number': 2, 'title': 'Button color off', 'body': 'The submit button is wrong color', 'labels': [], 'url': 'https://github.com/repo/issues/2'},
    {'number': 3, 'title': 'SQL injection vulnerability', 'body': 'Input not sanitized', 'labels': [], 'url': 'https://github.com/repo/issues/3'},
]


def _mock_settings(mock_get_settings):
    settings = MagicMock()
    settings.llm.model = 'gpt-4o'
    settings.mcp_servers.notion_page_id = 'test-page-id'
    mock_get_settings.return_value = settings


# ═══════════════════════════════════════════════════════════════════
# TriageAgent._classify_issues
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
@patch('agentforge.agents.triage_agent.get_settings')
@patch('agentforge.agents.triage_agent.get_llm')
class TestClassifyIssues:

    async def test_happy_path(self, mock_llm_cls, mock_get_settings):
        _mock_settings(mock_get_settings)
        agent = TriageAgent()
        mock_structured = MagicMock()
        mock_structured.ainvoke = AsyncMock(
            return_value=TriageResponse(items=[
                TriageItem(issue_number=1, severity='high', reason='broken'),
            ])
        )
        agent.llm = MagicMock()
        agent.llm.with_structured_output.return_value = mock_structured

        issues = [{"number": 1, "title": "Bug", "body": "It's broken"}]
        result = await agent._classify_issues(issues)

        assert len(result) == 1
        assert result[0]["severity"] == "high"
        assert result[0]["issue_number"] == 1

    async def test_llm_exception_returns_fallback(self, mock_llm_cls, mock_get_settings):
        """LLM raises an exception — should return safe fallback, not empty list."""
        _mock_settings(mock_get_settings)
        agent = TriageAgent()
        mock_structured = MagicMock()
        mock_structured.ainvoke = AsyncMock(side_effect=ValueError("parse error"))
        agent.llm = MagicMock()
        agent.llm.with_structured_output.return_value = mock_structured

        issues = [{"number": 1, "title": "Bug", "body": "body"}]
        result = await agent._classify_issues(issues)

        # Fallback returns one item per issue with severity 'low'
        assert len(result) == 1
        assert result[0]["severity"] == "low"
        assert result[0]["confidence"] == 0.0

    async def test_severity_normalized(self, mock_llm_cls, mock_get_settings):
        """Invalid severity in LLM output should be normalized to 'low'."""
        _mock_settings(mock_get_settings)
        agent = TriageAgent()
        mock_structured = MagicMock()
        mock_structured.ainvoke = AsyncMock(
            return_value=TriageResponse(items=[
                TriageItem(issue_number=1, severity='URGENT', reason='bad'),
            ])
        )
        agent.llm = MagicMock()
        agent.llm.with_structured_output.return_value = mock_structured

        issues = [{"number": 1, "title": "Bug", "body": "body"}]
        result = await agent._classify_issues(issues)

        assert len(result) == 1
        assert result[0]["severity"] == "low"

    async def test_multiple_items(self, mock_llm_cls, mock_get_settings):
        _mock_settings(mock_get_settings)
        agent = TriageAgent()
        mock_structured = MagicMock()
        mock_structured.ainvoke = AsyncMock(
            return_value=TriageResponse(items=[
                TriageItem(issue_number=1, severity='critical', reason='data loss'),
                TriageItem(issue_number=2, severity='medium', reason='perf'),
            ])
        )
        agent.llm = MagicMock()
        agent.llm.with_structured_output.return_value = mock_structured

        issues = [
            {"number": 1, "title": "A", "body": ""},
            {"number": 2, "title": "B", "body": ""},
        ]
        result = await agent._classify_issues(issues)

        assert len(result) == 2
        assert result[0]["severity"] == "critical"
        assert result[1]["severity"] == "medium"

    async def test_wontfix_severity(self, mock_llm_cls, mock_get_settings):
        """'wontfix' is a valid severity and should not be normalized."""
        _mock_settings(mock_get_settings)
        agent = TriageAgent()
        mock_structured = MagicMock()
        mock_structured.ainvoke = AsyncMock(
            return_value=TriageResponse(items=[
                TriageItem(issue_number=1, severity='wontfix', reason='duplicate'),
            ])
        )
        agent.llm = MagicMock()
        agent.llm.with_structured_output.return_value = mock_structured

        issues = [{"number": 1, "title": "Dup", "body": ""}]
        result = await agent._classify_issues(issues)

        assert result[0]["severity"] == "wontfix"


# ═══════════════════════════════════════════════════════════════════
# TriageAgent._build_report
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
@patch('agentforge.agents.triage_agent.get_settings')
@patch('agentforge.agents.triage_agent.get_llm')
class TestBuildReport:

    async def test_report_contains_all_severities(self, mock_llm_cls, mock_get_settings):
        _mock_settings(mock_get_settings)
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

    async def test_report_with_no_classified(self, mock_llm_cls, mock_get_settings):
        """Unclassified issues default to 'low' in the report."""
        _mock_settings(mock_get_settings)
        agent = TriageAgent()
        issues = [{"number": 1, "title": "Something", "url": "https://github.com/issues/1"}]
        classified = []
        report = agent._build_report(issues, classified)

        assert "LOW (1)" in report

    async def test_report_handles_wontfix(self, mock_llm_cls, mock_get_settings):
        _mock_settings(mock_get_settings)
        agent = TriageAgent()
        issues = [{"number": 1, "title": "Dup", "url": "https://github.com/issues/1"}]
        classified = [{"issue_number": 1, "severity": "wontfix", "reason": "dup"}]
        report = agent._build_report(issues, classified)

        assert "WONTFIX (1)" in report


# ═══════════════════════════════════════════════════════════════════
# TriageAgent._format_slack_alert
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
@patch('agentforge.agents.triage_agent.get_settings')
@patch('agentforge.agents.triage_agent.get_llm')
class TestSlackAlert:

    async def test_returns_string_not_tuple(self, mock_llm_cls, mock_get_settings):
        _mock_settings(mock_get_settings)
        agent = TriageAgent()
        classified = [
            {"severity": "critical"}, {"severity": "high"},
            {"severity": "medium"}, {"severity": "low"}, {"severity": "wontfix"},
        ]
        result = agent._format_slack_alert(classified, "https://notion.so/page")

        assert isinstance(result, str)
        assert "Bug Triage Complete" in result
        assert "Critical: 1" in result
        assert "https://notion.so/page" in result


# ═══════════════════════════════════════════════════════════════════
# TriageAgent.execute — full workflow integration tests
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
@patch('agentforge.agents.triage_agent.get_settings')
@patch('agentforge.agents.triage_agent.get_llm')
class TestTriageExecute:

    def _make_agent(self, mock_get_settings):
        _mock_settings(mock_get_settings)
        agent = TriageAgent()
        agent.github = MagicMock()
        agent.notion = MagicMock()
        agent.slack = MagicMock()
        agent.eval = MagicMock()
        agent.gate = MagicMock()
        agent.gate.ask = AsyncMock(return_value=True)
        return agent

    def _mock_structured_llm(self, agent, triage_response):
        """Helper: make agent.llm.with_structured_output().ainvoke() return the given response."""
        mock_structured = MagicMock()
        mock_structured.ainvoke = AsyncMock(return_value=triage_response)
        agent.llm = MagicMock()
        agent.llm.with_structured_output.return_value = mock_structured

    async def test_no_open_issues(self, mock_llm_cls, mock_get_settings):
        agent = self._make_agent(mock_get_settings)
        agent.github.list_issues.return_value = []

        result = await agent.execute('triage', SAMPLE_STATE)

        assert result['success'] is True
        assert 'No open issues' in result['output']

    async def test_happy_path_labels_applied(self, mock_llm_cls, mock_get_settings):
        agent = self._make_agent(mock_get_settings)
        agent.github.list_issues.return_value = SAMPLE_ISSUES[:2]
        agent.github.add_labels.return_value = True
        agent.notion.create_page.return_value = {"url": "https://notion.so/page"}

        self._mock_structured_llm(agent, TriageResponse(items=[
            TriageItem(issue_number=1, severity='critical', reason='data loss'),
            TriageItem(issue_number=2, severity='low', reason='cosmetic'),
        ]))

        result = await agent.execute('triage', SAMPLE_STATE)

        assert result['success'] is True
        assert agent.github.add_labels.call_count == 2
        assert any('severity:critical' in a for a in result['actions_taken'])
        assert any('severity:low' in a for a in result['actions_taken'])

    async def test_user_rejects_approval(self, mock_llm_cls, mock_get_settings):
        """If user rejects approval gate, no labels should be applied."""
        agent = self._make_agent(mock_get_settings)
        agent.github.list_issues.return_value = SAMPLE_ISSUES[:1]
        agent.gate.ask = AsyncMock(return_value=False)

        self._mock_structured_llm(agent, TriageResponse(items=[
            TriageItem(issue_number=1, severity='high', reason='broken'),
        ]))

        result = await agent.execute('triage', SAMPLE_STATE)

        assert result['success'] is False
        assert 'rejected' in result['output'].lower()
        agent.github.add_labels.assert_not_called()

    async def test_classification_failure_returns_fallback(self, mock_llm_cls, mock_get_settings):
        """If LLM classification fails, execute still succeeds with fallback low-severity labels."""
        agent = self._make_agent(mock_get_settings)
        agent.github.list_issues.return_value = SAMPLE_ISSUES[:1]
        agent.github.add_labels.return_value = True
        agent.notion.create_page.return_value = {"url": "https://notion.so/page"}

        # Structured LLM raises — _classify_issues returns fallback
        mock_structured = MagicMock()
        mock_structured.ainvoke = AsyncMock(side_effect=ValueError("LLM error"))
        agent.llm = MagicMock()
        agent.llm.with_structured_output.return_value = mock_structured

        result = await agent.execute('triage', SAMPLE_STATE)

        assert result['success'] is True
        # Fallback labels all issues as 'low'
        assert any('severity:low' in a for a in result['actions_taken'])

    async def test_label_failure_is_resilient(self, mock_llm_cls, mock_get_settings):
        """If add_labels fails for one issue, the rest still proceed."""
        agent = self._make_agent(mock_get_settings)
        agent.github.list_issues.return_value = SAMPLE_ISSUES[:2]
        agent.notion.create_page.return_value = {"url": "https://notion.so/page"}

        self._mock_structured_llm(agent, TriageResponse(items=[
            TriageItem(issue_number=1, severity='high', reason=''),
            TriageItem(issue_number=2, severity='low', reason=''),
        ]))

        # First call returns False (failure), second returns True
        agent.github.add_labels.side_effect = [False, True]

        result = await agent.execute('triage', SAMPLE_STATE)

        assert result['success'] is True
        assert agent.github.add_labels.call_count == 2
        # Only the second label should be in actions
        assert any('severity:low' in a for a in result['actions_taken'])
        assert not any('severity:high' in a for a in result['actions_taken'])
