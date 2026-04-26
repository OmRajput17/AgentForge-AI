# agentforge/orchestrator.py 

import json, asyncio
from langchain_core.messages import HumanMessage
from rich.console import Console
from rich.panel import Panel
from agentforge.agents.dev_agent import DevAgent
from agentforge.agents.triage_agent import TriageAgent
from agentforge.agents.standup_agent import StandupAgent
from agentforge.graph.state import AgentForgeState
from agentforge.config import get_settings, get_llm
from agentforge.logger import AgentLogger
from agentforge.agents.schemas import Plan, PlanItem

console = Console()

AGENT_REGISTRY = {
    "dev": DevAgent,
    "triage": TriageAgent,
    "standup": StandupAgent,
}

## Keyword fallback - used when LLM confidence < threshold

KEYWORD_MAPPING = {
    'triage': ['triage', 'bug', 'severity', 'label', 'issues'],
    'standup': ['standup', 'stand-up', 'daily', 'yesterday', 'today'],
    'dev': ['create issue', 'github issue', 'pull request', 'commit'],
}

class Orchestrator:
    def __init__(self):
        self.logger = AgentLogger('orchestrator')
        self.llm = get_llm(temperature=0)
        self._threshold = get_settings().confidence_threshold # default 0.8

    async def _decompose(self, task: str) -> list[dict]:
        '''LLM decomposes task + scores routing confidence (0.0–1.0).'''
        prompt = f'''You are an AI task planner.

            Break the user task into subtasks and assign each subtask to exactly one agent.

            For each subtask, return:
            - agent: one of ["dev", "triage", "standup"]
            - subtask: a clear, concise instruction
            - confidence: a float between 0.0 and 1.0 indicating how confident you are in the agent choice
            - parallel: true if this subtask can run independently of others, false otherwise

            Available agents:
            - dev: GitHub operations (create issue, list issues)
            - triage: bug triage workflow (fetch issues, classify, label, Notion, Slack)
            - standup: daily standup workflow (GitHub activity, Notion log, Slack post)

            Task: {task}

            Return structured output matching the schema.
            Do not include explanations or extra text.
        '''

        structured_llm = self.llm.with_structured_output(Plan)
        try:
            result = await structured_llm.ainvoke(prompt)
            subtasks = [item.model_dump() for item in result.items]
        except Exception as e:
            self.logger.error(f"Failed to decompose task: {e}")
            return []

        ## Apply keyword fallback for low-confidence routing
        for item in subtasks:
            try:
                conf = float(item.get('confidence', 1.0))
            except (TypeError, ValueError):
                conf = 1.0
            if conf < self._threshold:
                fallback = self._keyword_route(item['subtask'])
                if fallback:
                    self.logger.warn(
                        f'Low confidence ({conf:.2f}) for agent '
                        f'"{item["agent"]}" — overriding with keyword match "{fallback}"'
                    )

                    item['agent'] = fallback
                
        return subtasks
    
    def _keyword_route(self, subtask: str) -> str | None:
        '''Keyword fallback router — fires when LLM confidence is low.'''
        lower = subtask.lower()
        for agent, keywords in KEYWORD_MAPPING.items():
            if any(kw in lower for kw in keywords):
                return agent
        return None

    async def _run_subtasks(self, item: dict, state: AgentForgeState) -> dict:
        AgentCls = AGENT_REGISTRY.get(item['agent'])

        if not AgentCls:
            self.logger.warn(f'No Agent registered: {item["agent"]}')

            return {'agent': item['agent'], 'success': False, 'output':'Unknown agent'}

        try:
            result = await AgentCls().run(item['subtask'], state)
            return {
                'agent': item['agent'],
                **result
            }
        except Exception as e:
            self.logger.error(f"Agent {item['agent']} failed: {e}")
            return {'agent': item['agent'], 'success': False, 'output': f"Error: {str(e)}"}

    async def run(self, task: str):
        self.logger.info('Decomposing task...')
        subtasks = await self._decompose(task)
        if not subtasks:
            self.logger.warn("No subtasks generated")
            return
        self.logger.info(f'Found {len(subtasks)} subtask(s)')

        state: AgentForgeState = {
            'task': task, 'subtasks': subtasks, 'results': [],
            'current_agent': '', 'iteration': 0,
            'completed': False, 'audit_log': []
        }

        ## Seperate  parallel vs Sequential subtasks

        parallel = [s for s in subtasks if s.get('parallel', False)]
        sequential = [s for s in subtasks if not s.get('parallel', False)]

        async def execute():
            results = []

            ## Run parallel subtasks concurrently with asyncio.gather

            if parallel:
                self.logger.info(f'Running {len(parallel)} subtasks in parallel...')
                parallel_results = await asyncio.gather(
                    *[self._run_subtasks(item, state) for item in parallel],
                    return_exceptions = True
                )

                for r in parallel_results:
                    if isinstance(r, Exception):
                        self.logger.error(f'Parallel subtask failed: {r}')
                    else:
                        results.append(r)
                        state['audit_log'].extend(r.get('actions_taken', []))

            
            ## Run Sequential subtasks one by one
            for item in sequential:
                r = await self._run_subtasks(item, state = state)
                results.append(r)
                state['audit_log'].extend(r.get('actions_taken', []))

            state['results'] = results

        await execute()
        self._print_summary(state)

    def _print_summary(self, state: AgentForgeState):
        lines = ['']
        for r in state['results']:
            icon = '✅' if r['success'] else '❌'
            lines.append(f'{icon} [{r["agent"].upper()}]')
            lines.append(f'   {str(r["output"])[:200]}')
            lines.append('')
        lines.append(f'Actions taken: {len(state["audit_log"])}')
        for a in state['audit_log']:
            lines.append(f'  • {a}')
        console.print(Panel('\n'.join(lines), title='Run Complete', border_style='green'))

 