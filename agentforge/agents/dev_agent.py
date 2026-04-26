# agentforge/agents/dev_agent.py
import asyncio

from agentforge.agents.base import BaseAgent
from agentforge.agents.schemas import DevPlan
from agentforge.mcp.github_server import GitHubMCPServer
from agentforge.graph.state import AgentForgeState
from agentforge.config import get_settings, get_llm

class DevAgent(BaseAgent):
    '''Handles GitHub operations. Destructive — requires approval.'''

    def __init__(self):
        super().__init__('dev', destructive=True)
        self._github = GitHubMCPServer()

    async def execute(self, subtask: str, state: AgentForgeState) -> dict:
        llm    = get_llm(temperature=0)
        prompt = f'''For this GitHub task: {subtask}
                Choose ONE action: create_issue | list_issues | read_repo
                Return a JSON object with keys: action, title, body
            '''

        structured_llm = llm.with_structured_output(DevPlan)
        try:
            plan = await structured_llm.ainvoke(prompt)
        except Exception as e:
            self.logger.error(f'LLM parsing failed: {e}')
            return {'output': f'LLM error: {e}', 'success': False, 'actions_taken': []}

        action = plan.action  # already lowercased by validator

        if action == 'create_issue':
            r = await asyncio.to_thread(self._github.create_issue, plan.title, plan.body)
            return {'output': f'Issue created: {r["url"]}',
                    'success': True, 'actions_taken': [f'Created issue #{r["number"]}']}

        if action == 'list_issues':
            issues = await asyncio.to_thread(self._github.list_issues)
            return {'output': str(issues), 'success': True, 'actions_taken': ['Listed issues']}

        return {'output': 'Unknown action', 'success': False, 'actions_taken': []}
