import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from agentforge.agents.dev_agent import DevAgent

@pytest.mark.asyncio
@patch('agentforge.agents.dev_agent.ChatOpenAI')
async def test_dev_agent_create_issue(mock_llm):
    agent = DevAgent()
    # Mock MCP server actions
    agent._github = MagicMock()
    agent._github.create_issue.return_value = {'url': 'http://test', 'number': 42}
    
    # Mock LLM returning valid JSON
    mock_resp = MagicMock()
    mock_resp.content = '{"action": "create_issue", "title": "t", "body": "b"}'
    mock_llm.return_value.ainvoke = AsyncMock(return_value=mock_resp)

    res = await agent.execute('task', {})
    
    agent._github.create_issue.assert_called_once_with('t', 'b')
    assert res['success'] == True
    assert 'Issue created' in res['output']

@pytest.mark.asyncio
@patch('agentforge.agents.dev_agent.ChatOpenAI')
async def test_dev_agent_list_issues(mock_llm):
    agent = DevAgent()
    agent._github = MagicMock()
    agent._github.list_issues.return_value = [{'number': 1}]
    
    mock_resp = MagicMock()
    mock_resp.content = '{"action": "list_issues", "title": "", "body": ""}'
    mock_llm.return_value.ainvoke = AsyncMock(return_value=mock_resp)

    res = await agent.execute('task', {})
    
    agent._github.list_issues.assert_called_once()
    assert res['success'] == True
    assert "[{'number': 1}]" in res['output']

@pytest.mark.asyncio
@patch('agentforge.agents.dev_agent.ChatOpenAI')
async def test_dev_agent_unknown_action(mock_llm):
    agent = DevAgent()
    agent._github = MagicMock()
    
    mock_resp = MagicMock()
    mock_resp.content = '{"action": "invalid_action", "title": "", "body": ""}'
    mock_llm.return_value.ainvoke = AsyncMock(return_value=mock_resp)

    res = await agent.execute('task', {})
    
    assert res['success'] == False
    assert res['output'] == 'Unknown action'
