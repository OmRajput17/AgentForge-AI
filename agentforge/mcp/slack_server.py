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

    def _h(self) -> dict:
        return {
            'Authorization': f'Bearer {self._token}',
            'Content-Type': 'application/json',
        }
    
    def health_check(self) -> bool:
        r = self._resilient_get(
            self._client,
            f'{self.BASE}/auth.test',
            headers = self._h()
        )

        return r.json().get('ok', False)

    def send_message(self, channel: str, text: str)->dict:
        self._log_call(f'send_message → {channel}')
        r = self._resilient_post(
            self._client,
            f'{self.BASE}/chat.postMessage',
            headers = self._h(),
            json = {
                'channel':channel,
                'text': text
            }
        )

        d = r.json()
        if d.get('ok'):
            self.logger.success(f'Message sent to {channel}')
            return {'ok': True, 'ts': d.get('ts')}
        else:
            self.logger.error(f'Failed to send message: {d.get("error")}')
            return {'ok': False, 'error': d.get('error')}

    
    def list_channels(self) -> list[dict]:
        self._log_call('list_channels')
        r = self._resilient_get(
            self._client,
            f'{self.BASE}/conversations.list',
            headers = self._h()
        )

        return [{'id' : c['id'], 'name':c['name']} for c in r.json().get('channels', [])]
