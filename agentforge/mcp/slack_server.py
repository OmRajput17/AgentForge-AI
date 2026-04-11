# agentforge/mcp/slack_server.py

import httpx
from agentforge.mcp.base import BaseMCPServer
from agentforge.config import get_settings

class SlackMCPServer(BaseMCPServer):
    BASE = 'https://slack.com/api'

    def __init__(self):
        super().__init__('slack')
        self._token = get_settings().mcp_servers.slack_token
        self._client = httpx.Client(timeout=5.0)

    def _headers(self) -> dict:
        return {
            'Authorization': f'Bearer {self._token}',
            'Content-Type': 'application/json',
        }
    
    def health_check(self) -> bool:
        try:
            r = self._resilient_get(
                self._client,
                f'{self.BASE}/auth.test',
                headers=self._headers()
            )
            r.raise_for_status()

            data = r.json()
            return data.get('ok', False)

        except (ValueError, Exception):
            return False

    def send_message(self, channel: str, text: str)->dict:
        self._log_call(f'send_message → {channel}')
        r = self._resilient_post(
            self._client,
            f'{self.BASE}/chat.postMessage',
            headers = self._headers(),
            json = {
                'channel':channel,
                'text': text
            }
        )

        r.raise_for_status()    
        try:
            d = r.json()
        except ValueError:
            raise RuntimeError("Invalid JSON response from Slack")  
        if d.get('ok'):
            self.logger.success(f'Message sent to {channel}')
            return {'ok': True, 'ts': d.get('ts')}
        else:
            error = d.get('error')
            self.logger.error(f'Failed to send message: {error}')
            raise RuntimeError(f"Slack API error: {error}")

    def list_channels(self) -> list[dict]:
        self._log_call('list_channels')
        r = self._resilient_get(
            self._client,
            f'{self.BASE}/conversations.list',
            headers = self._headers()
        )

        r.raise_for_status()

        data = r.json()

        if not data.get('ok'):
            raise RuntimeError(f"Slack API error: {data.get('error')}")

        return [
            {'id': c.get('id'), 'name': c.get('name')}
            for c in data.get('channels', [])
        ]