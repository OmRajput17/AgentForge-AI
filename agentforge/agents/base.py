# agentforge/agents/base.py 

from abc import ABC, abstractmethod
from agentforge.graph.state import AgentForgeState
from agentforge.logger import AgentLogger
from agentforge.approval import ApprovalGate

class BaseAgent(ABC):
    '''
    Abstract base for all specialized agents.
    Subclasses define execute() and declare whether they are destructive.
    '''

    def __init__(self, name: str, destructive: bool = False):
        self.name = name
        self.destructive = destructive
        self.logger = AgentLogger(name)
        self.gate = ApprovalGate()

    @abstractmethod
    async def execute(self, subtask: str, state: AgentForgeState)-> dict:
        '''Execute a subtask. Must return {output, success, actions_taken}.'''
        ...

    async def run(self, subtask: str, state: AgentForgeState) -> dict:
        self.logger.info(f'Starting: {subtask}')

        if self.destructive:
            approved = await self.gate.ask(self.name, subtask)
            if not approved:
                self.logger.warn('Skipped -- User Declined')
                return {
                    'output':'Skipped by user',
                    'success' : False,
                    'actions_taken': []
                }
        result = await self.execute(subtask, state)

        if result.get('success'):
            self.logger.success('Done')

        return result

