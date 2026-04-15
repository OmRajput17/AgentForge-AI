import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from agentforge.agents.dev_agent import DevAgent
from agentforge.agents.schemas import DevPlan

@pytest.mark.asyncio
@patch('agentforge.agents.dev_agent.ChatOpenAI')
async def test_dev_agent_create_issue(mock_llm_cls):
    agent = DevAgent()
    # Mock MCP server actions
    agent._github = MagicMock()
    agent._github.create_issue.return_value = {'url': 'http://test', 'number': 42}
    
    # Mock structured LLM returning a DevPlan object
    mock_structured = MagicMock()
    mock_structured.ainvoke = AsyncMock(
        return_value=DevPlan(action='create_issue', title='t', body='b')
    )
    mock_llm_cls.return_value.with_structured_output.return_value = mock_structured

    res = await agent.execute('task', {})
    
    agent._github.create_issue.assert_called_once_with('t', 'b')
    assert res['success'] == True
    assert 'Issue created' in res['output']

@pytest.mark.asyncio
@patch('agentforge.agents.dev_agent.ChatOpenAI')
async def test_dev_agent_list_issues(mock_llm_cls):
    agent = DevAgent()
    agent._github = MagicMock()
    agent._github.list_issues.return_value = [{'number': 1}]
    
    mock_structured = MagicMock()
    mock_structured.ainvoke = AsyncMock(
        return_value=DevPlan(action='list_issues', title='', body='')
    )
    mock_llm_cls.return_value.with_structured_output.return_value = mock_structured

    res = await agent.execute('task', {})
    
    agent._github.list_issues.assert_called_once()
    assert res['success'] == True
    assert "[{'number': 1}]" in res['output']

@pytest.mark.asyncio
@patch('agentforge.agents.dev_agent.ChatOpenAI')
async def test_dev_agent_unknown_action(mock_llm_cls):
    agent = DevAgent()
    agent._github = MagicMock()
    
    mock_structured = MagicMock()
    mock_structured.ainvoke = AsyncMock(
        return_value=DevPlan(action='invalid_action', title='', body='')
    )
    mock_llm_cls.return_value.with_structured_output.return_value = mock_structured

    res = await agent.execute('task', {})
    
    assert res['success'] == False
    assert res['output'] == 'Unknown action'

@pytest.mark.asyncio
@patch('agentforge.agents.dev_agent.ChatOpenAI')
async def test_dev_agent_llm_failure(mock_llm_cls):
    """LLM raises an exception — agent should return gracefully."""
    agent = DevAgent()
    agent._github = MagicMock()
    
    mock_structured = MagicMock()
    mock_structured.ainvoke = AsyncMock(side_effect=ValueError("bad output"))
    mock_llm_cls.return_value.with_structured_output.return_value = mock_structured

    res = await agent.execute('task', {})
    
    assert res['success'] == False
    assert 'LLM error' in res['output']
