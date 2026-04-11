import pytest
from unittest.mock import patch, MagicMock
from agentforge.mcp.slack_server import SlackMCPServer

@pytest.fixture
def slack_server():
    with patch('agentforge.mcp.slack_server.get_settings') as mock_settings:
        mock_cfg = MagicMock()
        mock_cfg.mcp_servers.slack_token = "xoxb-fake-token"
        mock_settings.return_value = mock_cfg
        
        server = SlackMCPServer()
        server._client = MagicMock()
        yield server

def test_health_check_success(slack_server):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {'ok': True}
    slack_server._client.get.return_value = mock_resp

    assert slack_server.health_check() is True

def test_health_check_failure(slack_server):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {'ok': False, 'error': 'invalid_auth'}
    slack_server._client.get.return_value = mock_resp

    assert slack_server.health_check() is False

def test_send_message_success(slack_server):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {'ok': True, 'ts': '12345.6789'}
    slack_server._client.post.return_value = mock_resp

    res = slack_server.send_message("#general", "Hello world")
    assert res == {'ok': True, 'ts': '12345.6789'}
    
    slack_server._client.post.assert_called_once()
    args, kwargs = slack_server._client.post.call_args
    assert "chat.postMessage" in args[0]
    assert kwargs['json']['channel'] == "#general"
    assert kwargs['json']['text'] == "Hello world"

def test_send_message_failure(slack_server):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {'ok': False, 'error': 'channel_not_found'}
    slack_server._client.post.return_value = mock_resp

    with pytest.raises(RuntimeError, match="Slack API error: channel_not_found"):
        slack_server.send_message("#invalid", "Hello world")

def test_list_channels(slack_server):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        'ok': True,
        'channels': [{'id': 'C123', 'name': 'general'}, {'id': 'C456', 'name': 'random'}]
    }
    slack_server._client.get.return_value = mock_resp

    channels = slack_server.list_channels()
    assert len(channels) == 2
    assert channels[0]['id'] == 'C123'
    assert channels[0]['name'] == 'general'
