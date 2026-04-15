# agentforge/agents/standup_agent.py

from langchain_openai import ChatOpenAI
from agentforge.agents.base import BaseAgent
from agentforge.agents.schemas import Standup
from agentforge.mcp.github_server import GitHubMCPServer
from agentforge.mcp.notion_server import NotionMCPServer
from agentforge.mcp.slack_server import SlackMCPServer
from agentforge.graph.state import AgentForgeState
from agentforge.config import get_settings

class StandupAgent(BaseAgent):
    '''
    Daily Standup Workflow.
    1. Reads GitHub activity for the last 24 hours (commits, PRs, comments)
    2. Uses LLM to format it as a standup (Yesterday / Today / Blockers)
    3. Creates a Notion standup log entry
    4. Posts the standup to Slack automatically
    Destructive — posts to Slack, requires approval.
    '''

    def __init__(self):
        super().__init__('standup', destructive=True)
        self._github =  GitHubMCPServer()
        self._slack =  SlackMCPServer()
        self._notion =  NotionMCPServer()
        self._llm = ChatOpenAI(model = get_settings().llm.model, temperature = 0)


    def _summarise_events(self, events: list[dict]) -> str:
        """Convert raw github events into readable activity lines."""

        lines = []
        for e in events:
            etype = e['type']
            repo = e['repo']
            payload = e['payload']

            if etype == 'PushEvent':
                commits = payload.get('commits', [])
                for c in commits[:3]: #max 3 commits per push
                    lines.append(f'Pushed: {c["message"][:80]} in {repo}')

            elif etype == 'PullRequestEvent':
                pr = payload.get('pull_request', {})
                lines.append(f'PR {payload["action"]} : {pr.get("title", "")} in {repo}')

            elif etype == 'IssueEvent':
                issue = payload.get('issue', {})
                lines.append(f'Issue {payload["action"]} : {issue.get("title", "")} in {repo}')

            elif etype == 'IssueCommentEvent':
                lines.append(f'Commented on issue in {repo}')
        
        return '\n'.join(lines) if lines else 'No Github activity in last 24 hours.'


    async def _generate_standup(self, activity: str, username: str) -> Standup:
        """Use LLM to format activity as a structured Standup."""

        prompt = f'''Generate a daily standup from this GitHub activity.

            Developer: {username}
            Activity (last 24 hours):
            {activity}

            Provide:
            - yesterday: What was done — 2-3 concise bullet points
            - today: What is planned next — inferred from context
            - blockers: Any blockers visible from the activity (or "None")
        '''

        structured_llm = self._llm.with_structured_output(Standup)
        try:
            return await structured_llm.ainvoke(prompt)
        except Exception as e:
            self.logger.error(f'LLM standup generation failed: {e}')
            return Standup(
                yesterday='Unable to generate — LLM error',
                today='Unable to generate — LLM error',
                blockers='Unable to generate — LLM error',
            )

    def _format_slack_message(self, standup: Standup, username: str) -> str:
        return (
            f'📋 *Daily Standup — {username}*\n\n'
            f'*Yesterday:*\n{standup.yesterday}\n\n'
            f'*Today:*\n{standup.today}\n\n'
            f'*Blockers:*\n{standup.blockers}'
        )

    async def execute(self, subtask: str, state: AgentForgeState)->dict:
        actions = []

        cfg = get_settings().mcp_servers

        ## Step 1 : Get github username
        username = cfg.github_owner or 'unknown'

        ## Step 2 : fetch last 24 hours Github Activity
        self.logger.info(f'Fetching Github activity for {username}...')
        events = self._github.get_user_activity(username=username, since_hours=24)
        activity = self._summarise_events(events=events)
        self.logger.info(f'Found {len(events)} events.')
        actions.append(f'Fetched {len(events)} Github Events')

        ## Step 3 : Generate standup via LLM
        self.logger.info('Generating Standup with LLM...')
        standup = await self._generate_standup(activity=activity, username=username)
        actions.append("Standup Generated")

        ## Step 4 : Log to notion
        self.logger.info('Logging Standup to Notion...')
        if cfg.notion_token:
            content = (
                f'Yesterday:\n{standup.yesterday}\n\n'
                f'Today:\n{standup.today}\n\n'
                f'Blockers:\n{standup.blockers}\n\n'
            )

            page = self._notion.create_page(
                parent_id='YOUR_NOTION_PAGE_ID',
                title = f'Standup - {username}',
                content=content
            )

            actions.append(f'Notion log created: {page["url"]}')

        ## Step 5 : Post to slack
        self.logger.info('Posting standup to slack...')
        if cfg.slack_token:
            msg = self._format_slack_message(standup=standup, username=username)
            self._slack.send_message('#standup', msg)
            actions.append('Standup posted to #standup')

        output = (
            f'Yesterday:\n{standup.yesterday}\n\n'
            f'Today:\n{standup.today}\n\n'
            f'Blockers:\n{standup.blockers}\n\n'
        )

        return {'output': output, 'success':True, 'actions_taken':actions}
