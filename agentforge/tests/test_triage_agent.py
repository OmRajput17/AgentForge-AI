# agentforge/tests/test_triage_agent.py
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from agentforge.agents.triage_agent import (
    _safe_parse_json,
    _validate_classified,
    TriageAgent,
)


# ═══════════════════════════════════════════════════════════════════
# _safe_parse_json  — unit tests
# ═══════════════════════════════════════════════════════════════════

class TestSafeParseJson:
    """Tests for _safe_parse_json covering the greedy-regex fix and edge cases."""

    def test_plain_json_array(self):
        raw = '[{"number": 1, "severity": "high"}]'
        assert _safe_parse_json(raw) == [{"number": 1, "severity": "high"}]

    def test_fenced_json(self):
        raw = '```json\n[{"number": 2, "severity": "low"}]\n```'
        assert _safe_parse_json(raw) == [{"number": 2, "severity": "low"}]

    def test_fenced_no_language_tag(self):
        raw = '```\n[{"number": 3, "severity": "medium"}]\n```'
        assert _safe_parse_json(raw) == [{"number": 3, "severity": "medium"}]

    def test_surrounding_text(self):
        """JSON embedded in LLM prose should still be extracted."""
        raw = 'Here is the result:\n[{"number": 4, "severity": "critical"}]\nHope this helps!'
        result = _safe_parse_json(raw)
        assert result is not None
        assert result[0]["number"] == 4

    def test_non_greedy_regex(self):
        """
        The old greedy regex r'\\[.*\\]' would match from the first '[' to the
        LAST ']', swallowing extra text.  The non-greedy fix should capture
        only the first complete [...] block.
        """
        raw = '[{"number": 1, "severity": "high"}] some garbage ] more ]'
        result = _safe_parse_json(raw)
        # The direct json.loads on the full text fails, so it falls through
        # to the bracket regex.  Non-greedy should grab just the first array.
        assert result == [{"number": 1, "severity": "high"}]

    def test_returns_none_on_garbage(self):
        assert _safe_parse_json('not json at all') is None

    def test_returns_none_on_empty_string(self):
        assert _safe_parse_json('') is None

    def test_returns_none_on_dict(self):
        """A JSON object (dict) is not a list — should return None."""
        assert _safe_parse_json('{"number": 1}') is None

    def test_whitespace_only(self):
        assert _safe_parse_json('   \n\t  ') is None

    def test_multiple_arrays_picks_first(self):
        """With nested/multiple arrays in surrounding text, we get the first."""
        raw = 'prefix [{"a":1}] middle [{"b":2}] suffix'
        # Direct parse fails; bracket regex (non-greedy) grabs first [...]
        result = _safe_parse_json(raw)
        assert result == [{"a": 1}]


# ═══════════════════════════════════════════════════════════════════
# _validate_classified  — unit tests
# ═══════════════════════════════════════════════════════════════════

class TestValidateClassified:

    def test_valid_items(self):
        items = [
            {"number": 1, "severity": "critical", "reason": "data loss"},
            {"number": 2, "severity": "low", "reason": "typo"},
        ]
        result = _validate_classified(items)
        assert len(result) == 2
        assert result[0] == {"number": 1, "severity": "critical", "reason": "data loss"}
        assert result[1] == {"number": 2, "severity": "low", "reason": "typo"}

    def test_invalid_severity_defaults_to_low(self):
        items = [{"number": 5, "severity": "URGENT"}]
        result = _validate_classified(items)
        assert result[0]["severity"] == "low"

    def test_missing_severity_defaults_to_low(self):
        items = [{"number": 6}]
        result = _validate_classified(items)
        assert result[0]["severity"] == "low"
        assert result[0]["reason"] == ""

    def test_non_int_number_skipped(self):
        items = [{"number": "not-a-number", "severity": "high"}]
        assert _validate_classified(items) == []

    def test_missing_number_skipped(self):
        items = [{"severity": "high"}]
        assert _validate_classified(items) == []

    def test_non_dict_items_skipped(self):
        items = ["string", 42, None, True]
        assert _validate_classified(items) == []

    def test_empty_list(self):
        assert _validate_classified([]) == []

    def test_mixed_valid_invalid(self):
        items = [
            {"number": 1, "severity": "high"},
            "garbage",
            {"number": "x", "severity": "low"},
            {"number": 3, "severity": "medium"},
        ]
        result = _validate_classified(items)
        assert len(result) == 2
        assert result[0]["number"] == 1
        assert result[1]["number"] == 3

    def test_severity_case_insensitive(self):
        items = [{"number": 10, "severity": "  HIGH  "}]
        result = _validate_classified(items)
        assert result[0]["severity"] == "high"


# ═══════════════════════════════════════════════════════════════════
# TriageAgent._classify_issues  — async unit tests
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
@patch('agentforge.agents.triage_agent.ChatOpenAI')
class TestClassifyIssues:

    async def test_happy_path(self, mock_llm_cls):
        agent = TriageAgent()
        mock_resp = MagicMock()
        mock_resp.content = '[{"number": 1, "severity": "high", "reason": "broken"}]'
        agent._llm = MagicMock()
        agent._llm.ainvoke = AsyncMock(return_value=mock_resp)

        issues = [{"number": 1, "title": "Bug", "body": "It's broken"}]
        result = await agent._classify_issues(issues)

        assert len(result) == 1
        assert result[0]["severity"] == "high"
        assert result[0]["number"] == 1

    async def test_none_content_returns_empty(self, mock_llm_cls):
        """resp.content is None — our new guard should prevent a crash."""
        agent = TriageAgent()
        mock_resp = MagicMock()
        mock_resp.content = None
        agent._llm = MagicMock()
        agent._llm.ainvoke = AsyncMock(return_value=mock_resp)

        issues = [{"number": 1, "title": "Bug", "body": "body"}]
        result = await agent._classify_issues(issues)

        assert result == []

    async def test_empty_string_content_returns_empty(self, mock_llm_cls):
        """resp.content is '' — falsy, same guard catches it."""
        agent = TriageAgent()
        mock_resp = MagicMock()
        mock_resp.content = ''
        agent._llm = MagicMock()
        agent._llm.ainvoke = AsyncMock(return_value=mock_resp)

        issues = [{"number": 1, "title": "Bug", "body": "body"}]
        result = await agent._classify_issues(issues)

        assert result == []

    async def test_unparseable_content_returns_empty(self, mock_llm_cls):
        agent = TriageAgent()
        mock_resp = MagicMock()
        mock_resp.content = 'Sorry, I cannot classify these issues.'
        agent._llm = MagicMock()
        agent._llm.ainvoke = AsyncMock(return_value=mock_resp)

        issues = [{"number": 1, "title": "Bug", "body": "body"}]
        result = await agent._classify_issues(issues)

        assert result == []

    async def test_fenced_llm_response(self, mock_llm_cls):
        """LLM wraps JSON in markdown fences — should still parse."""
        agent = TriageAgent()
        mock_resp = MagicMock()
        mock_resp.content = '```json\n[{"number": 7, "severity": "medium", "reason": "slow"}]\n```'
        agent._llm = MagicMock()
        agent._llm.ainvoke = AsyncMock(return_value=mock_resp)

        issues = [{"number": 7, "title": "Slow page", "body": ""}]
        result = await agent._classify_issues(issues)

        assert len(result) == 1
        assert result[0]["severity"] == "medium"


# ═══════════════════════════════════════════════════════════════════
# TriageAgent._build_report  — async unit tests
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
@patch('agentforge.agents.triage_agent.ChatOpenAI')
class TestBuildReport:

    async def test_report_contains_all_severities(self, mock_llm_cls):
        agent = TriageAgent()
        issues = [
            {"number": 1, "title": "Critical bug"},
            {"number": 2, "title": "Minor typo"},
        ]
        classified = [
            {"number": 1, "severity": "critical", "reason": "data loss"},
            {"number": 2, "severity": "low", "reason": "cosmetic"},
        ]
        report = await agent._build_report(issues, classified)

        assert "Bug Triage Report" in report
        assert "CRITICAL (1)" in report
        assert "LOW (1)" in report
        assert "#1" in report
        assert "#2" in report

    async def test_report_with_no_classified(self, mock_llm_cls):
        """Unclassified issues default to 'low' in the report."""
        agent = TriageAgent()
        issues = [{"number": 1, "title": "Something"}]
        classified = []
        report = await agent._build_report(issues, classified)

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

        mock_resp = MagicMock()
        mock_resp.content = '[{"number":1,"severity":"critical","reason":"data loss"},{"number":2,"severity":"medium","reason":"perf"}]'
        agent._llm = MagicMock()
        agent._llm.ainvoke = AsyncMock(return_value=mock_resp)

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

        mock_resp = MagicMock()
        mock_resp.content = None  # LLM returns None
        agent._llm = MagicMock()
        agent._llm.ainvoke = AsyncMock(return_value=mock_resp)

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

        mock_resp = MagicMock()
        mock_resp.content = '[{"number":1,"severity":"high","reason":""},{"number":2,"severity":"low","reason":""}]'
        agent._llm = MagicMock()
        agent._llm.ainvoke = AsyncMock(return_value=mock_resp)

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

        mock_resp = MagicMock()
        mock_resp.content = '[{"number":1,"severity":"high","reason":"bad"}]'
        agent._llm = MagicMock()
        agent._llm.ainvoke = AsyncMock(return_value=mock_resp)

        result = await agent.execute('triage', {})

        assert result['success'] is True
        agent._notion.create_page.assert_called_once()
        agent._slack.send_message.assert_called_once()
        assert any('Notion' in a for a in result['actions_taken'])
        assert any('Slack' in a for a in result['actions_taken'])
