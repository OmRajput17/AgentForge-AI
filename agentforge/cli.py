import typer
from rich.console import Console
from rich.panel import Panel
from agentforge.config import init_config, get_settings, CONFIG_FILE

app = typer.Typer(help='AgentForge - Multi Agent Orchestration over MCP')
console = Console()

@app.command()
def init():
    '''Initialize AgentForge config at ~/.agentforge/config.yml'''
    init_config()
    console.print(Panel(
        f'[green]Config created at[/green] {CONFIG_FILE}\n'
        '[dim]Edit it to add your API keys and MCP tokens.[/dim]',
        title='AgentForge Init', border_style='blue'
    ))

@app.command()
def run(task: str = typer.Argument(..., help='Task in plain english')):
    '''Run a multi-agent workflow for the given task'''
    from agentforge.orchestrator import Orchestrator
    console.print(Panel(f'[bold]{task}[/bold]', title='Task', border_style='cyan'))
    Orchestrator().run(task)

@app.command()
def server():
    """List configured MCP servers and their connections status"""
    cfg = get_settings().mcp_servers
    rows = [
        ('GitHub',  bool(cfg.github_token)),
        ('Notion',  bool(cfg.notion_token)),
        ('Slack',   bool(cfg.slack_token)),
        ('Tavily',  bool(cfg.tavily_api)),
    ]
    for name, ok in rows:
        status = '[green]✅ configured[/green]' if ok else '[red]❌ not configured[/red]'
        console.print(f'  {name:<12} {status}')

if __name__=="__main__":
    app()

