## agentforge/mcp/github_server.py

import httpx
from datetime import datetime, timedelta
from agentforge.mcp.base import BaseMCPServer
from agentforge.config import get_settings

class GitHubMCPServer(BaseMCPServer):
    '''
    MCP server wrapping the GitHub REST API.
    Exposes: create_issue, list_issues, add_label, get_user_activity, read_repo
    '''

    BASE = 'https://api.github.com'

    def __init__(self):
        super().__init__('github')
        cfg =   get_settings().mcp_servers
        self._headers = {
            'Authorization' : f'Bearer {cfg.github_token}',
            'Accept' : 'application/vnd.github+json',
            'X-GitHub-Api-Version': '2022-11-28'
        }
        self._owner = cfg.github_owner
        self._repo = cfg.github_repo
        self._client = httpx.Client(timeout=5.0)

    def health_check(self) -> bool:
        try:
            r = self._resilient_get(self._client, f'{self.BASE}/user', headers=self._headers)
            return True
        except Exception:
            return False

    def create_issue(self,title: str,body: str,owner: str = "",repo: str = "") -> dict:
        o,r = owner or self._owner, repo or self._repo
        self._log_call(f'create_issue → {o}/{r}')
        resp = self._resilient_post(
            self._client,
            f'{self.BASE}/repos/{o}/{r}/issues',
            headers=self._headers,
            json={'title':title,'body' : body}
        )
        resp.raise_for_status()
        d = resp.json()
        self.logger.success(f'Issue #{d["number"]} created: {d["html_url"]}')
        return {'number':d['number'], 'url':d['html_url']}
    
    def list_issues(self, state = 'open', owner: str = "", repo: str = "")->list[dict]:
        o, r = owner or self._owner, repo or self._repo
        self._log_call(f'list issues ({state}) → {o}/{r}')
        resp = self._resilient_get(
            self._client,
            f'{self.BASE}/repos/{o}/{r}/issues',
            headers=self._headers,
            params={'state': state, 'per_page':50}
        )
        resp.raise_for_status()
        return [
            {
                'number': i['number'],
                'title': i['title'],
                'body': i.get('body',''),
                'labels': [l['name'] for l in i['labels']],
                'url': i['html_url']
            }
            for i in resp.json()
        ]

    def add_labels(self, issue_number: int, labels: list[str], owner: str = "", repo: str = "") -> bool:
        o, r = owner or self._owner, repo or self._repo
        self._log_call(f'add_labels #{issue_number} → {labels}')
        resp = self._resilient_post(
            self._client,
            f'{self.BASE}/repos/{o}/{r}/issues/{issue_number}/labels',
            headers = self._headers,
            json = {'labels': labels}
        )
        return resp.status_code == 200
    
    def get_user_activity(self, username: str, since_hours: int = 24)-> list[dict]:
        '''Get commits and events for a user in the last N hours.'''
        self._log_call(f'get_user_activity → {username} (last {since_hours}h)')
        since = (datetime.utcnow() - timedelta(hours = since_hours)).isoformat() + 'Z'

        resp = self._resilient_get(
            self._client,
            f'{self.BASE}/users/{username}/events',
            headers=self._headers,
            params={'per_page': 30}
        )
        resp.raise_for_status()

        events = []
        for e in resp.json():
            if e['created_at'] >= since:
                events.append({
                    'type':    e['type'],
                    'repo':    e['repo']['name'],
                    'created': e['created_at'],
                    'payload': e.get('payload', {})
                })
        return events

    def post_comments(self, issue_number: int, body: str, owner:str = "", repo:str = "")->dict:
        o, r = owner or self._owner, repo or self._repo
        self._log_call(f'post_comment → #{issue_number}')
        resp = self._resilient_post(
            self._client,
            f'{self.BASE}/repos/{o}/{r}/issues/{issue_number}/comments',
            headers=self._headers, json={'body': body}
        )
        resp.raise_for_status()
        return resp.json()
