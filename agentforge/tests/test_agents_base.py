import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from agentforge.agents.base import BaseAgent
from agentforge.graph.state import AgentForgeState

class TestAgent(BaseAgent):
    def __init__(self, destructive=False):
        super().__init__('test_agent', destructive=destructive)

    async def execute(self, subtask: str, state: AgentForgeState) -> dict:
        return {'output': 'test_out', 'success': True, 'actions_taken': ['did_test']}

@pytest.mark.asyncio
async def test_non_destructive_runs_immediately():
    agent = TestAgent(destructive=False)
    state = {}
    res = await agent.run('do task', state)
    assert res['success'] == True
    assert res['output'] == 'test_out'

@pytest.mark.asyncio
@patch('agentforge.approval.ApprovalGate.ask', new_callable=AsyncMock)
async def test_destructive_runs_if_approved(mock_ask):
    mock_ask.return_value = True
    agent = TestAgent(destructive=True)
    state = {}
    res = await agent.run('do task', state)
    mock_ask.assert_called_once_with('test_agent', 'do task')
    assert res['success'] == True

@pytest.mark.asyncio
@patch('agentforge.approval.ApprovalGate.ask', new_callable=AsyncMock)
async def test_destructive_skips_if_declined(mock_ask):
    mock_ask.return_value = False
    agent = TestAgent(destructive=True)
    state = {}
    res = await agent.run('do task', state)
    mock_ask.assert_called_once_with('test_agent', 'do task')
    assert res['success'] == False
    assert res['output'] == 'Skipped by user'
