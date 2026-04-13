import pytest
from unittest.mock import patch, MagicMock
from agentforge.approval import ApprovalGate

@pytest.mark.asyncio
@patch('agentforge.approval.get_settings')
async def test_auto_approve_true(mock_get_settings):
    # Mock settings.auto_approve
    settings = MagicMock()
    settings.auto_approve = True
    mock_get_settings.return_value = settings

    gate = ApprovalGate()
    result = await gate.ask('test_agent', 'do something')
    assert result is True

@pytest.mark.asyncio
@patch('agentforge.approval.get_settings')
@patch('agentforge.approval.Confirm.ask')
async def test_auto_approve_false_delegates_to_cli(mock_ask, mock_get_settings):
    # Mock settings.auto_approve
    settings = MagicMock()
    settings.auto_approve = False
    mock_get_settings.return_value = settings

    # Simulate user typing 'y' inside the thread
    mock_ask.return_value = True

    gate = ApprovalGate()
    result = await gate.ask('test_agent', 'do something')
    
    # Confirm.ask should have been called
    assert mock_ask.call_count == 1
    assert result is True
