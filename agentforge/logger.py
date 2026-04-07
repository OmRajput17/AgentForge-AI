from rich.console import Console
from rich.panel import Panel

console = Console()

AGENT_COLORS = {
    'orchestrator': 'bold cyan',
    'research':     'bold green',
    'writer':       'bold yellow',
    'dev':          'bold magenta',
    'comms':        'bold blue',
    'triage':       'bold red',
    'standup':      'bold white',
}

class AgentLogger:
    def __init__(self, agent_name: str):
        self.name = agent_name
        self.color = AGENT_COLORS.get(agent_name, 'white')

    def info(self, msg: str):
        console.print(f'[{self.color}][{self.name.upper()}][/{self.color}] {msg}')

    def success(self, msg: str):
        console.print(f'[{self.color}][{self.name.upper()}][/{self.color}] [green]✅ {msg}[/green]')

    def warn(self, msg: str):
        console.print(f'[{self.color}][{self.name.upper()}][/{self.color}] [yellow]⚠️  {msg}[/yellow]')

    def error(self, msg: str):
        console.print(f'[{self.color}][{self.name.upper()}][/{self.color}] [red]❌   {msg}[/red]')

    def mcp_call(self, server: str, action: str):
        console.print(f'[{self.color}][{self.name.upper()}][/{self.color}] [dim]→ MCP:{server}[/dim] {action}')
    