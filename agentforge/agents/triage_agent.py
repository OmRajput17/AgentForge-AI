# agentforge/agents/triage_agent.py
import asyncio
import uuid
from datetime import datetime
from langchain_core.messages import HumanMessage
from agentforge.agents.base import BaseAgent
from agentforge.mcp.github_server import GitHubMCPServer
from agentforge.mcp.notion_server import NotionMCPServer
from agentforge.mcp.slack_server import SlackMCPServer
from agentforge.graph.state import AgentForgeState
from agentforge.eval_engine import EvalEngine
from agentforge.config import get_settings, get_llm
from agentforge.logger import AgentLogger
from agentforge.agents.schemas import TriageItem, TriageResponse

class TriageAgent(BaseAgent):
    '''
        Full bug triage workflow:
        1. Fetch all open GitHub issues
        2. Classify each by severity via LLM (with confidence score)
        3. Apply labels on GitHub
        4. Generate triage report + create Notion page
        5. Alert #engineering on Slack
        6. Log all predictions to EvalEngine
    '''

    def __init__(self):
        super().__init__('triage', destructive=True)
        self.github = GitHubMCPServer()
        self.notion = NotionMCPServer()
        self.slack = SlackMCPServer()
        self.eval = EvalEngine()
        self.llm = get_llm(temperature=0)
        self.run_id = str(uuid.uuid4())[:8]
    
    async def execute(self, subtask: str, state: AgentForgeState) -> dict:
        actions = []

        # Step 1: Fetch Issues (blocking MCP → thread)
        issues = await asyncio.to_thread(self.github.list_issues, state='open')
        self.logger.info(f'Found {len(issues)} open issues.')
        actions.append(f'github.list_issue → {len(issues)} issues.')

        if not issues:
            return {
                'success': True,
                'output':'No open issues found.',
                'actions_taken': actions
            }
        
        # Step 2: Classify with confidence scores
        classified = await self._classify_issues(issues)

        # Step 3: Log to EvalEngine BEFORE taking actions
        for issue, clss in zip(issues, classified):
            self.eval.log_triage(
                issue_number= issue['number'],
                issue_title=issue['title'],
                predicted= clss['severity'],
                confidence= clss.get('confidence', 1.0),
                run_id=self.run_id
            )
        
        # Step 4: Approval Gate before writing to GitHub
        approved = await self.gate.ask("triage", f"Label {len(issues)} GitHub issues?")
        if not approved:
            return {
                'success': False,
                'output': 'User rejected GitHub label actions.',
                'actions_taken': actions
            }
        
        # Step 5: Apply Labels (blocking MCP → thread)
        for issue, clss in zip(issues, classified):
            label = f'severity:{clss["severity"]}'
            ok = await asyncio.to_thread(
                self.github.add_labels,
                issue_number=issue['number'],
                labels=[label]
            )
            if ok:
                actions.append(f'github.add_labels → {label}')
            else:
                self.logger.warn(f'Failed to add label to issue {issue["number"]}')

        
        # Step 6: Generate Report + Notion Page (blocking MCP → thread)
        cfg = get_settings().mcp_servers
        report = self._build_report(issues, classified)
        page_url = None

        if cfg.notion_token and cfg.notion_page_id:
            try:
                page = await asyncio.to_thread(
                    self.notion.create_page,
                    parent_id=cfg.notion_page_id,
                    title = f'Bug Triage Report - {datetime.now().strftime("%Y-%m-%d")} - run {self.run_id}',
                    content= report
                )
                page_url = page["url"]
                actions.append(f'notion.create_page → {page_url}')
            except Exception as e:
                self.logger.warn(f'Notion failed (non-fatal): {e}')
        else:
            self.logger.warn('Skipping Notion — token or page_id not configured')

        # Step 7: Slack alert (blocking MCP → thread)
        critical = [c for c in classified if c['severity'] == 'critical']
        if cfg.slack_token:
            try:
                slack_msg = self._format_slack_alert(classified, page_url or 'N/A')
                await asyncio.to_thread(
                    self.slack.send_message,
                    channel=cfg.slack_channel,
                    text = slack_msg
                )
                actions.append(f'slack.send_message → #{cfg.slack_channel}')
            except Exception as e:
                self.logger.warn(f'Slack failed (non-fatal): {e}')
        else:
            self.logger.warn('Skipping Slack — token not configured')

        # Step 8: Print eval summary
        self.eval.print_report(run_id=self.run_id)

        return {
            'success' : True,
            'output' : f'Triaged {len(issues)} issues. {len(critical)} critical.' + (f' Report: {page_url}' if page_url else ''),
            'actions_taken': actions
        }

    async def _classify_issues(self, issues: list[dict]) -> list[dict]:
        '''
        Batch classify all issues in ONE LLM call.
        Returns confidence score per classification.
        Batching = 90% API cost reduction vs calling LLM per issue.
        '''

        issues_text = '\n'.join(
            f'Issue #{i["number"]}: {i["title"]}\nBody: {(i["body"] or "")[:200]}'
            for i in issues
        )

        prompt = f'''
            Classify the following GitHub issues by severity.
            Return a JSON list with the same order as the input.
            
            Issues:
            {issues_text}

            Severity Levels:
            - critical: Production down, data loss, security breach
            - high: Major functionality broken, no workaround
            - medium: Important feature impaired, workaround exists
            - low: Cosmetic, typo, minor UX issue
            - wontfix: Duplicate, invalid, not a bug

            Return a JSON list of objects with:
            {{
                "issue_number": int,
                "severity": "critical|high|medium|low|wontfix",
                "confidence": 0.0-1.0,
                "reason": "Short explanation"
            }}
            confidence is 0.0-1.0 for how certain you are of the severity label.
            Return ONLY the JSON, no prose.
        '''

        try:
            structured_llm = self.llm.with_structured_output(TriageResponse)
            result = await structured_llm.ainvoke(prompt)
            return [item.model_dump() for item in result.items]
        except Exception as e:
            self.logger.error(f'LLM classification failed: {e}')
            # Safe fallback: mark all issues as low severity
            return [
                {
                    "issue_number": issue["number"],
                    "severity": "low",
                    "confidence": 0.0,
                    "reason": "Fallback — LLM classification failed"
                }
                for issue in issues
            ]

    def _build_report(self, issues: list[dict], classified: list[dict]) -> str:
        by_severity = {'critical': [], 'high': [], 'medium': [], 'low': [], 'wontfix': []}
        cls_map = {c['issue_number']: c for c in classified}
        for issue in issues:
            cls = cls_map.get(issue["number"], {})
            sev = cls.get("severity", "low")
            by_severity.setdefault(sev, []).append(
                f'#{issue["number"]}: {issue["title"]}\n'
                f'  Reason: {cls.get("reason", "-")}\n'
                f'  URL: {issue["url"]}\n'
            )
        
        lines = [f'Bug Triage Report -- Run {self.run_id}', "=" * 50]
        for sev in ['critical', 'high', 'medium', 'low', 'wontfix']:
            items = by_severity.get(sev, [])
            lines.append(f'\n{sev.upper()} ({len(items)})')
            lines.extend(items if items else ['(none)'])
        
        return '\n'.join(lines)

    def _format_slack_alert(self, classified: list[dict], notion_url: str)->str:
        critical = [c for c in classified if c['severity'] == 'critical']
        high = [c for c in classified if c['severity'] == 'high']
        medium = [c for c in classified if c['severity'] == 'medium']
        low = [c for c in classified if c['severity'] == 'low']
        wontfix = [c for c in classified if c['severity'] == 'wontfix']

        return (
            f':rotating_light: *Bug Triage Complete* (run {self.run_id})\n'
            f'Critical: {len(critical)} | High: {len(high)} | Medium: {len(medium)} | Low: {len(low)} | Won\'t Fix: {len(wontfix)} | Total: {len(classified)}\n'
            f'Full Triage Report: {notion_url}'
        )
        


