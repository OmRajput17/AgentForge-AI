# agentforge/agents/dev_agent.py
import json
import asyncio
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from agentforge.agents.base import BaseAgent
from agentforge.mcp.github_server import GitHubMCPServer
from agentforge.graph.state import AgentForgeState
from agentforge.config import get_settings

class DevAgent(BaseAgent):
    '''Handles GitHub operations. Destructive — requires approval.'''

    def __init__(self):
        super().__init__('dev', destructive=True)
        self._github = GitHubMCPServer()

    async def execute(self, subtask: str, state: AgentForgeState) -> dict:
        llm    = ChatOpenAI(model=get_settings().llm.model, temperature=0)
        prompt = f'''For this GitHub task: {subtask}
                Choose ONE action: create_issue | list_issues | read_repo
                Return JSON: {{"action": "", "title": "", "body": ""}}
            '''
        plan = json.loads((await llm.ainvoke([HumanMessage(content=prompt)])).content)

        if plan['action'] == 'create_issue':
            r = await asyncio.to_thread(self._github.create_issue, plan['title'], plan['body'])
            return {'output': f'Issue created: {r["url"]}',
                    'success': True, 'actions_taken': [f'Created issue #{r["number"]}']}

        if plan['action'] == 'list_issues':
            issues = await asyncio.to_thread(self._github.list_issues)
            return {'output': str(issues), 'success': True, 'actions_taken': ['Listed issues']}

        return {'output': 'Unknown action', 'success': False, 'actions_taken': []}
