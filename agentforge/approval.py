import asyncio
from rich.console import Console
from rich.prompt import Confirm
from agentforge.config import get_settings

console = Console()

class ApprovalGate:

    async def ask(self, agent_name: str, action: str) -> bool:
        if get_settings().auto_approve:
            return True

        console.print(f'\n[yellow]⚠️  [{agent_name.upper()}] about to execute:[/yellow]')
        console.print(f'   [bold]{action}[/bold]')

        try:
            return await asyncio.to_thread(
                Confirm.ask, 'Approve?', default=False
            )
        except KeyboardInterrupt:
            return False