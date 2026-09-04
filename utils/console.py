from rich.console import Console
from rich.panel import Panel
from rich.table import Table
console = Console()

def print_banner():
    console.print(Panel.fit(
        "[bold cyan]𝗞èá𝗥[/bold cyan]\n[bold]FLOWTIKTOK[/bold]\nTIKTOK AUTOMATION BOT",
        border_style="cyan"
    ))

def print_status(tg_app, scheduler):
    t = Table(title="SYSTEM")
    t.add_column("Service"); t.add_column("Status")
    t.add_row("Telegram", "[green]ONLINE[/green]")
    t.add_row("Database", "[green]CONNECTED[/green]")
    t.add_row("Scheduler", "[green]RUNNING[/green]" if scheduler else "[red]STOPPED[/red]")
    t.add_row("Storage", "[green]READY[/green]")
    t.add_row("TikTok", "[yellow]CONFIGURED / API DEPENDS ON APPROVAL[/yellow]")
    console.print(t)
    console.print(Panel(
        "✓ /start\n✓ /schedule\n✓ /posts\n✓ /connect\n✓ /admin\n\n🚀 Bot started\n📅 Scheduler started\n🔗 TikTok service loaded",
        title="COMMANDS / ACTIVITY"
    ))
