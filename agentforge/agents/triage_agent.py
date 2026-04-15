# agentforge/agents/triage_agent.py
import asyncio
from langchain_openai import ChatOpenAI
from agentforge.agents.base import BaseAgent
from agentforge.agents.schemas import TriageItem, TriageResponse
from agentforge.mcp.github_server import GitHubMCPServer
from agentforge.mcp.notion_server import NotionMCPServer
from agentforge.mcp.slack_server import SlackMCPServer
from agentforge.graph.state import AgentForgeState
from agentforge.config import get_settings

VALID_SEVERITIES = {'critical', 'high', 'medium', 'low'}


class TriageAgent(BaseAgent):
    '''
    Bug Triage Workflow.
    1. Fetches all open GitHub issues
    2. Uses LLM to classify each by severity (critical/high/medium/low)
    3. Adds severity labels back to GitHub
    4. Creates a Notion triage report page
    5. Posts a summary to Slack
    Destructive — adds labels and posts messages, requires approval.
    '''

    SEVERITY_LABELS = ['severity:critical', 'severity:high', 'severity:medium', 'severity:low']

    def __init__(self):
        super().__init__('triage', destructive=True)
        self._github = GitHubMCPServer()
        self._notion = NotionMCPServer()
        self._slack = SlackMCPServer()
        self._llm = ChatOpenAI(
            model = get_settings().llm.model,
            temperature = 0
        )

    async def _classify_issues(self, issues: list[dict]) -> list[dict]:
        """
        Ask LLM to classify issues by severity using structured output.
        Returns a list of validated dicts, or [] on failure.
        """
        issues_text = '\n'.join(
            f'#{i.get("number", "?")}: {i.get("title", "")} -- {(i.get("body") or "")[:200]}'
            for i in issues
        )

        prompt = f'''Classify each GitHub issue by severity.
                Severity levels: critical | high | medium | low

                Rules:
                - critical: system down, data loss, security vulnerability
                - high: major feature broken, significant user impact
                - medium: partial functionality affected, workaround exists
                - low: cosmetic, minor inconvenience, enhancement

                Issues:
                {issues_text}

                Return the classified issues as a JSON object with an "items" key
                containing an array of objects, each with "number", "severity", and "reason".
            '''

        structured_llm = self._llm.with_structured_output(TriageResponse)
        try:
            result = await structured_llm.ainvoke(prompt)
        except Exception as e:
            self.logger.error(f'LLM classification failed: {e}')
            return []

        # Convert Pydantic models to dicts for downstream compatibility
        return [item.model_dump() for item in result.items]

    async def _build_report(self, issues: list[dict], classified: list[dict]) -> str:
        """
        Build a markdown report from classified issues.
        """
        severity_map = {c['number']: c for c in classified}
        sections = {
            'critical':[],
            'high':[],
            'medium':[],
            'low':[]
        }

        for issue in issues:
            info = severity_map.get(issue.get('number'), {})
            sev = info.get('severity', 'low')
            if sev not in VALID_SEVERITIES:
                sev = 'low'
            sections[sev].append(
                f'#{issue.get("number", "?")} — {issue.get("title", "")} ({info.get("reason","")})'
            )

        lines = ['Bug Triage Report', '']
        for sev, items in sections.items():
            if items:
                lines.append(f'{sev.upper()} ({len(items)})')
                lines.extend(f'  • {item}' for item in items)
                lines.append('')
        return '\n'.join(lines)

    async def execute(self, subtask: str, state: AgentForgeState)->dict:
        actions = []

        # Step 1 : Fetch all open issues
        self.logger.info('Fetching open GitHub issues...')
        try:
            issues = await asyncio.to_thread(self._github.list_issues, state='open')
        except Exception as e:
            self.logger.error(f'Failed to fetch GitHub issues: {e}')
            return {
                'output': f'Failed to fetch issues: {e}',
                'success': False,
                'actions_taken': actions
            }

        self.logger.info(f"Found {len(issues)} open issues")
        actions.append(f"Fetched {len(issues)} issues from GitHub")

        if not issues:
            return {
                'output': 'No open issues found.',
                'success': True,
                'actions_taken': actions
            }

        # Step 2 : Classify by severity
        self.logger.info("Classifying issues by severity...")
        try:
            classified = await self._classify_issues(issues=issues)
        except Exception as e:
            self.logger.error('Classification failed: %s', e)
            classified = []

        if classified:
            actions.append(f'Classified {len(classified)} issues')
        else:
            self.logger.warn('No issues were classified — skipping labeling')

        # Step 3 : Add severity labels back to GitHub
        self.logger.info('Adding severity labels to GitHub issues...')
        for item in classified:
            label = f'severity:{item["severity"]}'
            if label not in self.SEVERITY_LABELS:
                self.logger.warn(f'Skipping invalid label {label} for #{item["number"]}')
                continue
            try:
                await asyncio.to_thread(self._github.add_labels, item['number'], [label])
                actions.append(f'Labeled #{item["number"]} as {label}')
            except Exception as e:
                self.logger.error(f'Failed to label #{item["number"]}: {e}')

        # Step 4 : Build triage report
        report = await self._build_report(issues, classified)

        # Step 5 : Create Notion page
        self.logger.info('Creating triage report in Notion...')
        try:
            notion_cfg = get_settings().mcp_servers
            if notion_cfg.notion_token:
                page = await asyncio.to_thread(
                    self._notion.create_page,
                    parent_id='YOUR_NOTION_PAGE_ID',  # set in config
                    title='Bug Triage Report',
                    content=report,
                )
                actions.append(f'Notion page created: {page.get("url", "unknown")}')
        except Exception as e:
            self.logger.error(f'Failed to create Notion page: {e}')

        # Step 6: Post summary to Slack
        self.logger.info('Posting summary to Slack...')
        critical = sum(1 for c in classified if c.get('severity') == 'critical')
        high = sum(1 for c in classified if c.get('severity') == 'high')
        medium = sum(1 for c in classified if c.get('severity') == 'medium')
        low = sum(1 for c in classified if c.get('severity') == 'low')

        slack_msg = (
            f'🔴 Bug Triage Complete\n'
            f'Total: {len(issues)} issues | '
            f'Critical: {critical} | High: {high} | Medium: {medium} | Low: {low}\n'
            f'Full report in Notion.'
        )

        try:
            if get_settings().mcp_servers.slack_token:
                await asyncio.to_thread(self._slack.send_message, "#engineering", slack_msg)
                actions.append("Slack notification sent to #engineering")
        except Exception as e:
            self.logger.error(f'Failed to send Slack message: {e}')

        return {
            'output': report,
            'success': True,
            'actions_taken': actions
        }
