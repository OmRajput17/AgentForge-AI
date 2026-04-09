import pytest
import asyncio
from unittest.mock import MagicMock, patch
from tenacity import RetryError
from agentforge.mcp.base import CircuitBreaker, BaseMCPServer, CircuitOpenError

class DummyServer(BaseMCPServer):
    def health_check(self) -> bool:
        return True

def test_circuit_breaker_success():
    cb = CircuitBreaker()
    cb._failures = 2
    cb.call_succeeded()
    assert cb._failures == 0
    assert not cb.is_open()

def test_circuit_breaker_failure():
    cb = CircuitBreaker(max_failures=3)
    cb.call_failed()
    cb.call_failed()
    assert not cb.is_open()
    cb.call_failed()
    assert cb.is_open()

def test_circuit_breaker_timeout():
    cb = CircuitBreaker(max_failures=1, reset_timeout=0.1)
    cb.call_failed()
    assert cb.is_open()
    
    # Mock loop time forward
    loop = asyncio.get_event_loop()
    original_time = loop.time
    loop.time = MagicMock(return_value=original_time() + 1.0)
    
    assert not cb.is_open()
    
    loop.time = original_time

def test_base_server_resilient_get_success():
    server = DummyServer("test")
    client = MagicMock()
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    client.get.return_value = mock_response
    
    res = server._resilient_get(client, "http://test.com")
    assert res == mock_response
    assert server._circuit._failures == 0
    assert client.get.call_count == 1

def test_base_server_circuit_open_raises():
    server = DummyServer("test")
    client = MagicMock()
    server._circuit._open = True
    server._circuit._open_at = asyncio.get_event_loop().time()
    
    with pytest.raises(CircuitOpenError, match="Circuit open for test - skipping call"):
        server._resilient_get(client, "http://test.com")

def test_log_call():
    server = DummyServer("test")
    with patch.object(server.logger, "mcp_call") as mock_logger:
        server._log_call("action_test")
        mock_logger.assert_called_once_with("test", action="action_test")
