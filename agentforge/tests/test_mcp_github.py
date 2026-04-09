import pytest
from unittest.mock import patch, MagicMock
from agentforge.mcp.github_server import GitHubMCPServer

@pytest.fixture
def github_server():
    # Patch get_settings to simulate a valid configuration without needing config.yml
    with patch('agentforge.mcp.github_server.get_settings') as mock_settings:
        mock_cfg = MagicMock()
        mock_cfg.mcp_servers.github_token = "fake-token"
        mock_cfg.mcp_servers.github_owner = "test-owner"
        mock_cfg.mcp_servers.github_repo = "test-repo"
        mock_settings.return_value = mock_cfg
        
        server = GitHubMCPServer()
        # Mock the internal httpx client to prevent any real network requests over the internet
        server._client = MagicMock()
        yield server

def test_health_check(github_server):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.raise_for_status.return_value = None
    github_server._client.get.return_value = mock_resp

    assert github_server.health_check() is True

def test_create_issue(github_server):
    mock_resp = MagicMock()
    mock_resp.status_code = 201
    mock_resp.json.return_value = {'number': 42, 'html_url': 'http://fakegithub/42'}
    github_server._client.post.return_value = mock_resp

    res = github_server.create_issue("Test issue", "Test body")
    
    # Assert network request paths and payloads
    github_server._client.post.assert_called_once()
    args, kwargs = github_server._client.post.call_args
    assert "repos/test-owner/test-repo/issues" in args[0]
    assert kwargs['json']['title'] == "Test issue"
    assert kwargs['json']['body'] == "Test body"
    
    # Assert custom response format
    assert res == {'number': 42, 'url': 'http://fakegithub/42'}

def test_list_issues(github_server):
    mock_resp = MagicMock()
    mock_resp.json.return_value = [
        {'number': 1, 'title': 'bug', 'body': 'fix', 'labels': [{'name': 'urgent'}], 'html_url': 'http://fake1'}
    ]
    github_server._client.get.return_value = mock_resp

    issues = github_server.list_issues(state='open')
    assert len(issues) == 1
    assert issues[0]['number'] == 1
    assert issues[0]['labels'] == ['urgent']

def test_add_labels(github_server):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    github_server._client.post.return_value = mock_resp

    res = github_server.add_labels(1, ['bug', 'help'])
    assert res is True
    
    args, kwargs = github_server._client.post.call_args
    assert args[0].endswith("/issues/1/labels")
    assert kwargs['json']['labels'] == ['bug', 'help']

def test_get_user_activity(github_server):
    mock_resp = MagicMock()
    # Return a mocked future date so it guarantees hitting the > since_hours threshold
    mock_resp.json.return_value = [
        {
            'type': 'PushEvent',
            'repo': {'name': 'test-repo'},
            'created_at': '2050-01-01T00:00:00Z', 
            'payload': {}
        }
    ]
    github_server._client.get.return_value = mock_resp

    events = github_server.get_user_activity('testuser', since_hours=24)
    assert len(events) == 1
    assert events[0]['type'] == 'PushEvent'

def test_post_comments(github_server):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {'id': 999}
    github_server._client.post.return_value = mock_resp

    res = github_server.post_comments(1, "Comment body")
    assert res == {'id': 999}
    
    args, kwargs = github_server._client.post.call_args
    assert kwargs['json']['body'] == "Comment body"
