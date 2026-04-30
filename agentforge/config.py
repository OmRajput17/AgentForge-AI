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
    notion_page_id: str = ""
    slack_token: str = ""
    slack_channel: str = "general"  ## default Slack channel for alerts
    github_owner: str = "" ## default repo owner
    github_repo: str = "" ## default repo name

class Settings(BaseModel):
    llm: LLMConfig = LLMConfig()
    mcp_servers: MCPServerConfig = MCPServerConfig()
    auto_approve: bool = False
    confidence_threshold: float = 0.8
    max_iterations: int = 10
    standup_lookback_hours: int = 24  ## how far back to fetch activity


@lru_cache
def get_settings() -> Settings:
    if not CONFIG_FILE.exists():
        return Settings()
    with open(CONFIG_FILE) as f:
        data = yaml.safe_load(f)
    return Settings(**data)


def get_llm(temperature: float = 0):
    '''Factory: returns the right LangChain chat model based on config provider.'''
    cfg = get_settings().llm
    if cfg.provider == 'groq':
        from langchain_groq import ChatGroq
        return ChatGroq(
            model=cfg.model,
            api_key=cfg.api_key,
            temperature=temperature,
        )
    else:
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=cfg.model,
            temperature=temperature,
        )


def init_config():
    CONFIG_DIR.mkdir(exist_ok=True)
    if CONFIG_FILE.exists():
        return
    default = {
        'llm': {'provider':'openai','model':'gpt-4o','api_key':''},
        'mcp_servers': {
            'github_token':'','notion_token':'','notion_page_id':'',
            'slack_token':'','slack_channel':'general',
            'github_owner':'','github_repo':''
        },
        'auto_approve': False,
        'confidence_threshold': 0.8,
        'max_iterations': 10,
        'standup_lookback_hours': 24
    }
    with open(CONFIG_FILE,'w') as f:
        yaml.dump(default, f, default_flow_style=False)

