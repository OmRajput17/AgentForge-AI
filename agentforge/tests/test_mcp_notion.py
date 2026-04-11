import pytest
from unittest.mock import patch, MagicMock
from agentforge.mcp.notion_server import NotionMCPServer

@pytest.fixture
def notion_server():
    with patch('agentforge.mcp.notion_server.get_settings') as mock_settings:
        mock_cfg = MagicMock()
        mock_cfg.mcp_servers.notion_token = "secret_fake_token"
        mock_settings.return_value = mock_cfg
        
        server = NotionMCPServer()
        server._client = MagicMock()
        yield server

def test_health_check(notion_server):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    notion_server._client.get.return_value = mock_resp

    assert notion_server.health_check() is True

def test_create_page(notion_server):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {'id': 'notion-page-id', 'url': 'http://notion/test'}
    notion_server._client.post.return_value = mock_resp

    res = notion_server.create_page("parent_id_123", "Task 1", "To do content")
    assert res == {'id': 'notion-page-id', 'url': 'http://notion/test'}

    notion_server._client.post.assert_called_once()
    args, kwargs = notion_server._client.post.call_args
    assert "pages" in args[0]
    
    payload = kwargs['json']
    assert payload['parent']['page_id'] == "parent_id_123"
    assert payload['properties']['title']['title'][0]['text']['content'] == "Task 1"

def test_search_page(notion_server):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        'results': [
            {'id': 'page1', 'url': 'http://notion/page1'},
            {'id': 'page2', 'url': 'http://notion/page2'}
        ]
    }
    notion_server._client.post.return_value = mock_resp

    results = notion_server.search_page("Project")
    assert len(results) == 2
    assert results[0]['id'] == 'page1'
    assert results[1]['id'] == 'page2'
    
    args, kwargs = notion_server._client.post.call_args
    assert "search" in args[0]
    assert kwargs['json']['query'] == "Project"
