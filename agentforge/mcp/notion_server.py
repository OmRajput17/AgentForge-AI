# agentforge/mcp/notion_server.py

import httpx
from agentforge.mcp.base import BaseMCPServer
from agentforge.config import get_settings

class NotionMCPServer(BaseMCPServer):
    BASE = 'https://api.notion.com/v1'

    def __init__(self):
        super().__init__('notion')
        token = get_settings().mcp_servers.notion_token
        self._headers = {
            'Authorization': f'Bearer {token}',
            'Notion-Version' : '2022-06-28',
            'Content-Type': 'application/json',
        }
        self._client = httpx.Client(timeout=5.0)

    def health_check(self) -> bool:
        try:
            r = self._resilient_get(self._client, f'{self.BASE}/users/me', headers = self._headers)
            return r.status_code == 200
        except Exception:
            return False

    def create_page(self, parent_id: str, title: str, content: str) -> dict:
        self._log_call(f'create_page → {title}')
        payload = {
            'parent' : {'page_id':parent_id},
            'properties': {'title': {'title': [{'text': {'content': title}}]}},
            'children' : [{'object':'block', 'type':'paragraph', 'paragraph':{'rich_text': [{'text': {'content':content}}]}}]
        }

        r = self._resilient_post(
            self._client,
            f'{self.BASE}/pages',
            headers = self._headers,
            json = payload
        )
        r.raise_for_status()
        d = r.json()
        self.logger.success(f'Page created: {d["url"]}')
        return {'id' : d['id'], 'url':d['url']}

    def search_page(self, query: str) -> list[dict]:
        self._log_call(f'search → {query}')

        r = self._resilient_post(
            self._client,
            f'{self.BASE}/search',
            headers = self._headers,
            json = {'query':query}
        )

        r.raise_for_status()
        return [{'id':p['id'],'url':p['url']} for p in r.json().get('results',[])]
