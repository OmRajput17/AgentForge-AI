import yaml
from pathlib import Path
from pydantic import BaseModel
from functools import lru_cache

CONFIG_DIR = Path.home() / '.agentforge'
CONFIG_FILE = CONFIG_DIR / 'config.yml'


class LLMConfig(BaseModel):
    provider : str = 'openai'
    model: str = "gpt-4o"
    api_key: str = ''

class MCPServerConfig(BaseModel):
    github_token: str = ""
    notion_token: str = ""
    slack_token: str = ""
    tavily_api: str = ""
    github_owner: str = "" ## default repo owner
    github_repo: str = "" ## default repo name

class Settings(BaseModel):
    llm: LLMConfig = LLMConfig()
    mcp_servers: MCPServerConfig = MCPServerConfig()
    auto_approve: bool = False
    confidence_threshold: float = 0.8
    max_iterations: int = 10


@lru_cache
def get_settings() -> Settings:
    if not CONFIG_FILE.exists():
        return Settings()
    with open(CONFIG_FILE) as f:
        data = yaml.safe_load(f)
    return Settings(**data)

def init_config():
    CONFIG_DIR.mkdir(exist_ok=True)
    if CONFIG_FILE.exists():
        return
    default = {
        'llm': {'provider':'openai','model':'gpt-4o','api_key':''},
        'mcp_servers': {
            'github_token':'','notion_token':'','slack_token':'','tavily_key':'',
            'github_owner':'','github_repo':''
        },
        'auto_approve': False,
        'confidence_threshold': 0.8,
        'max_iterations': 10
    }
    with open(CONFIG_FILE,'w') as f:
        yaml.dump(default, f, default_flow_style=False)
