#!/usr/bin/env python3
"""
🌪️ Smart HRRR Interactive CLI
Beautiful, feature-rich command-line interface for HRRR weather data processing
"""

import typer
import questionary
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.prompt import Prompt, Confirm
from rich.layout import Layout
from rich.align import Align
from rich.text import Text
from rich.columns import Columns
from rich.rule import Rule
from rich.tree import Tree
from rich import box
from datetime import datetime, timedelta
from pathlib import Path
import subprocess
import os
import sys
import multiprocessing as mp
from typing import Optional, List
import time

# Initialize Rich console
console = Console()
app = typer.Typer(
    name="hrrr-cli",
    help="🌪️ Smart HRRR Interactive Weather Data Processor",
    add_completion=False,
    rich_markup_mode="rich"
)

# Available categories and their emojis
CATEGORIES = {
    "severe": "🌪️ Severe Weather",
    "instability": "⚡ Instability", 
    "smoke": "🔥 Smoke & Fire",
    "surface": "🌡️ Surface",
    "reflectivity": "📡 Reflectivity",
    "heat": "🌡️ Heat Stress",
    "atmospheric": "☁️ Atmospheric",
    "precipitation": "🌧️ Precipitation",
    "composites": "📊 Composites",
    "updraft_helicity": "🌀 Updraft Helicity",
    "upper_air": "🎈 Upper Air"
}

WORKFLOWS = {
    "severe_outbreak": "🌪️ Severe Weather Analysis",
    "fire_monitoring": "🔥 Fire Weather Monitoring", 
    "nowcasting": "⛈️ Nowcasting Setup",
    "heat_analysis": "🌡️ Heat Stress Analysis",
    "research": "📊 Research Dataset",
    "monitoring": "🎯 Operational Monitoring"
}

def show_banner():
    """Display the application banner"""
    banner = Text.from_markup(
        "[bold blue]🌪️ Smart HRRR Interactive CLI[/bold blue]\n"
        "[dim]High-Performance Weather Data Processing & Visualization[/dim]"
    )
    console.print(Panel(
        Align.center(banner),
        box=box.DOUBLE,
        style="blue",
        padding=(1, 2)
    ))

def show_system_info():
    """Display system information"""
    cpu_count = mp.cpu_count()
    
    info_table = Table(show_header=False, box=None, padding=(0, 1))
    info_table.add_column("", style="cyan")
    info_table.add_column("", style="white")
    
    info_table.add_row("🖥️ CPUs Available:", f"{cpu_count} cores")
    info_table.add_row("📅 Current Time:", datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC"))
    info_table.add_row("📁 Working Dir:", str(Path.cwd()))
    
    console.print(Panel(info_table, title="System Info", border_style="green"))

def get_recent_dates():
    """Get list of recent dates for selection"""
    today = datetime.now()
    dates = []
    for i in range(7):  # Last 7 days
        date = today - timedelta(days=i)
        dates.append(date.strftime("%Y%m%d"))
    return dates

def select_categories() -> List[str]:
    """Interactive category selection"""
    console.print("\n[bold cyan]Available Categories:[/bold cyan]")
    
    # Display categories with numbers
    categories_list = list(CATEGORIES.items())
    for i, (key, emoji_name) in enumerate(categories_list, 1):
        console.print(f"  {i:2}. {emoji_name}")
    
    console.print(f"  {len(categories_list)+1:2}. [bold green]All categories[/bold green]")
    console.print("   0. [bold red]Skip[/bold red]")
    
    # Get user selection
    while True:
        try:
            selection = Prompt.ask(
                "\n[bold]Enter category numbers (comma-separated, e.g., 1,3,5) or 0 to skip[/bold]",
                default="0"
            )
            
            if selection == "0":
                return []
            
            if selection == str(len(categories_list)+1):
                return list(CATEGORIES.keys())
            
            # Parse comma-separated numbers
            numbers = [int(x.strip()) for x in selection.split(",")]
            selected_keys = []
            
            for num in numbers:
                if 1 <= num <= len(categories_list):
                    selected_keys.append(categories_list[num-1][0])
                else:
                    console.print(f"[red]Invalid number: {num}[/red]")
                    continue
            
            if selected_keys:
                # Show selected categories
                console.print("\n[bold green]Selected categories:[/bold green]")
                for key in selected_keys:
                    console.print(f"  ✓ {CATEGORIES[key]}")
                return selected_keys
            else:
                console.print("[yellow]No valid categories selected. Try again.[/yellow]")
                
        except ValueError:
            console.print("[red]Invalid input. Please enter numbers separated by commas.[/red]")

def select_workflow():
    """Select a predefined workflow"""
    console.print("\n[bold cyan]Available Workflows:[/bold cyan]")
    
    workflows_list = list(WORKFLOWS.items())
    for i, (key, emoji_name) in enumerate(workflows_list, 1):
        console.print(f"  {i}. {emoji_name}")
    
    while True:
        try:
            selection = Prompt.ask(
                f"\n[bold]Choose workflow (1-{len(workflows_list)})[/bold]",
                default="1"
            )
            
            num = int(selection)
            if 1 <= num <= len(workflows_list):
                selected_key = workflows_list[num-1][0]
                console.print(f"\n[bold green]Selected:[/bold green] {WORKFLOWS[selected_key]}")
                return selected_key
            else:
                console.print(f"[red]Please enter a number between 1 and {len(workflows_list)}[/red]")
                
        except ValueError:
            console.print("[red]Invalid input. Please enter a number.[/red]")

def show_processing_progress(title: str, duration: int = 10):
    """Show a progress bar for processing"""
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task(title, total=duration)
        for i in range(duration):
            time.sleep(0.1)  # Simulate work
            progress.advance(task)

@app.command("interactive")
def interactive_mode():
    """🎮 Launch interactive mode with guided workflows"""
    console.clear()
    show_banner()
    show_system_info()
    
    console.print("\n" + "="*60)
    console.print("[bold yellow]Welcome to Interactive Mode![/bold yellow]")
    console.print("="*60)
    
    # Main menu loop
    while True:
        console.print()
        action = questionary.select(
            "What would you like to do?",
            choices=[
                questionary.Choice("🚀 Process Latest HRRR Data", value="latest"),
                questionary.Choice("📅 Process Specific Date/Hour", value="specific"),
                questionary.Choice("⚡ Quick Workflows", value="workflow"),
                questionary.Choice("🎬 Create Animations (GIFs)", value="gifs"),
                questionary.Choice("📊 System Status", value="status"),
                questionary.Choice("❌ Exit", value="exit")
            ],
            style=questionary.Style([
                ('question', 'bold'),
                ('answer', 'fg:#ff9d00 bold'),
                ('pointer', 'fg:#ff9d00 bold'),
                ('highlighted', 'fg:#ff9d00 bold'),
            ])
        ).ask()
        
        if action == "exit":
            console.print("[bold green]Thanks for using Smart HRRR CLI! 🌪️[/bold green]")
            break
        elif action == "latest":
            process_latest_interactive()
        elif action == "specific":
            process_specific_interactive()
        elif action == "workflow":
            run_workflow_interactive()
        elif action == "gifs":
            create_gifs_interactive()
        elif action == "status":
            show_system_status()

def process_latest_interactive():
    """Interactive latest data processing"""
    console.print(Panel("[bold blue]🚀 Processing Latest HRRR Data[/bold blue]", style="blue"))
    
    # Select categories
    categories = select_categories()
    if not categories:
        console.print("[yellow]No categories selected. Skipping...[/yellow]")
        return
    
    # Select forecast hours
    hours_choice = questionary.select(
        "Select forecast hour range:",
        choices=[
            "0-6 (Nowcasting)",
            "0-12 (Short-term)",
            "0-18 (Standard)",
            "0-48 (Extended)",
            "Custom"
        ]
    ).ask()
    
    if hours_choice == "Custom":
        hours = questionary.text("Enter hour range (e.g., 0-12 or 0,3,6):").ask()
    else:
        hours = hours_choice.split()[0]
    
    # Select worker count
    max_workers = mp.cpu_count()
    workers = questionary.select(
        f"Select number of workers (max {max_workers}):",
        choices=[str(i) for i in [1, 2, 4, max_workers//2, max_workers]]
    ).ask()
    
    # Confirm and execute
    cmd_parts = [
        "python", "processor_cli.py", "--latest",
        "--categories", ",".join(categories),
        "--hours", hours,
        "--workers", workers
    ]
    
    console.print(f"\n[bold green]Command to execute:[/bold green]")
    console.print(f"[dim]{' '.join(cmd_parts)}[/dim]")
    
    if Confirm.ask("\nProceed with processing?"):
        console.print("\n[bold blue]🚀 Processing started...[/bold blue]")
        result = subprocess.run(cmd_parts, capture_output=False)
        
        if result.returncode == 0:
            console.print("\n[bold green]✅ Processing completed successfully![/bold green]")
        else:
            console.print("\n[bold red]❌ Processing failed![/bold red]")

def process_specific_interactive():
    """Interactive specific date/hour processing"""
    console.print(Panel("[bold blue]📅 Process Specific Date/Hour[/bold blue]", style="blue"))
    
    # Date selection
    recent_dates = get_recent_dates()
    date_choice = questionary.select(
        "Select date:",
        choices=recent_dates + ["Custom date"]
    ).ask()
    
    if date_choice == "Custom date":
        date = questionary.text("Enter date (YYYYMMDD):").ask()
    else:
        date = date_choice
    
    # Hour selection
    hour = questionary.select(
        "Select model run hour:",
        choices=[f"{h:02d}" for h in [0, 1, 2, 3, 6, 12, 18, 21]]
    ).ask()
    
    # Rest similar to latest processing
    categories = select_categories()
    if not categories:
        console.print("[yellow]No categories selected. Skipping...[/yellow]")
        return
    
    hours_choice = questionary.select(
        "Select forecast hour range:",
        choices=["0-6", "0-12", "0-18", "0-48", "Custom"]
    ).ask()
    
    if hours_choice == "Custom":
        hours = questionary.text("Enter hour range:").ask()
    else:
        hours = hours_choice
    
    workers = questionary.select(
        f"Workers (max {mp.cpu_count()}):",
        choices=["1", "2", "4", "8"]
    ).ask()
    
    cmd_parts = [
        "python", "processor_cli.py", 
        date, hour,
        "--categories", ",".join(categories),
        "--hours", hours,
        "--workers", workers
    ]
    
    console.print(f"\n[bold green]Command:[/bold green] [dim]{' '.join(cmd_parts)}[/dim]")
    
    if Confirm.ask("Execute?"):
        console.print("\n[bold blue]🚀 Processing...[/bold blue]")
        subprocess.run(cmd_parts)

def run_workflow_interactive():
    """Run predefined workflows"""
    console.print(Panel("[bold blue]⚡ Quick Workflows[/bold blue]", style="blue"))
    
    workflow = select_workflow()
    if not workflow:
        return
    
    # Get parameters for the workflow
    if workflow == "severe_outbreak":
        console.print("[bold yellow]🌪️ Severe Weather Analysis Workflow[/bold yellow]")
        date = questionary.text("Date (YYYYMMDD):", default=datetime.now().strftime("%Y%m%d")).ask()
        hour = questionary.select("Hour:", choices=["00", "06", "12", "18"]).ask()
        
        cmd = f"python processor_cli.py {date} {hour} --hours 0-24 --categories severe,instability --workers 8"
        
    elif workflow == "fire_monitoring":
        console.print("[bold yellow]🔥 Fire Weather Monitoring Workflow[/bold yellow]") 
        cmd = "python processor_cli.py --latest --categories smoke,fire --hours 0-6"
        
    elif workflow == "nowcasting":
        console.print("[bold yellow]⛈️ Nowcasting Workflow[/bold yellow]")
        cmd = "python processor_cli.py --latest --categories reflectivity,surface,severe --hours 0-3 --workers 4"
        
    elif workflow == "heat_analysis":
        console.print("[bold yellow]🌡️ Heat Stress Analysis Workflow[/bold yellow]")
        date = questionary.text("Date:", default=datetime.now().strftime("%Y%m%d")).ask()
        cmd = f"python processor_cli.py {date} 12 --hours 0-48 --categories heat,surface --workers 6"
        
    elif workflow == "research":
        console.print("[bold yellow]📊 Research Dataset Workflow[/bold yellow]")
        date = questionary.text("Date:", default=datetime.now().strftime("%Y%m%d")).ask()
        cmd = f"python processor_cli.py {date} 00 --hours 0-48 --workers 8"
        
    elif workflow == "monitoring":
        console.print("[bold yellow]🎯 Operational Monitoring[/bold yellow]")
        cmd = "python monitor_continuous.py"
    
    console.print(f"\n[bold green]Command:[/bold green] [dim]{cmd}[/dim]")
    
    if Confirm.ask("Execute workflow?"):
        console.print("\n[bold blue]🚀 Running workflow...[/bold blue]")
        subprocess.run(cmd.split())

def create_gifs_interactive():
    """Interactive GIF creation"""
    console.print(Panel("[bold blue]🎬 Create Animations (GIFs)[/bold blue]", style="blue"))
    
    # Check for existing processed data
    output_dir = Path("outputs/hrrr")
    if not output_dir.exists():
        console.print("[red]No processed data found in outputs/hrrr/[/red]")
        return
    
    # List available dates
    available_dates = [d.name for d in output_dir.iterdir() if d.is_dir()]
    available_dates.sort(reverse=True)
    
    if not available_dates:
        console.print("[red]No processed dates found![/red]")
        return
    
    # Select date
    date = questionary.select(
        "Select date for GIF creation:",
        choices=available_dates[:10]  # Show last 10 dates
    ).ask()
    
    # List available hours for selected date
    date_dir = output_dir / date
    available_hours = [h.name for h in date_dir.iterdir() if h.is_dir()]
    available_hours.sort()
    
    if not available_hours:
        console.print(f"[red]No processed hours found for {date}![/red]")
        return
    
    hour = questionary.select(
        "Select hour:",
        choices=available_hours
    ).ask()
    
    # Select categories for GIF creation
    categories = select_categories()
    if not categories:
        console.print("[yellow]No categories selected for GIFs.[/yellow]")
        return
    
    # Select max hours and duration
    max_hours = questionary.select(
        "Maximum forecast hours for animation:",
        choices=["6", "12", "18", "24", "48"]
    ).ask()
    
    duration = questionary.select(
        "Animation speed (ms per frame):",
        choices=[
            questionary.Choice("Fast (200ms)", value="200"),
            questionary.Choice("Normal (250ms)", value="250"), 
            questionary.Choice("Slow (400ms)", value="400"),
            questionary.Choice("Very Slow (500ms)", value="500")
        ]
    ).ask()
    
    # Execute GIF creation
    cmd_parts = [
        "python", "tools/create_gifs.py",
        date, hour,
        "--categories", ",".join(categories),
        "--max-hours", max_hours,
        "--duration", duration
    ]
    
    console.print(f"\n[bold green]GIF Command:[/bold green] [dim]{' '.join(cmd_parts)}[/dim]")
    
    if Confirm.ask("Create GIFs?"):
        console.print("\n[bold blue]🎬 Creating animations...[/bold blue]")
        result = subprocess.run(cmd_parts)
        
        if result.returncode == 0:
            gif_dir = f"outputs/hrrr/{date}/{hour}/animations"
            console.print(f"\n[bold green]✅ GIFs created successfully![/bold green]")
            console.print(f"[dim]Check: {gif_dir}/[/dim]")
        else:
            console.print("\n[bold red]❌ GIF creation failed![/bold red]")

def show_system_status():
    """Show system status and recent outputs"""
    console.print(Panel("[bold blue]📊 System Status[/bold blue]", style="blue"))
    
    # Check outputs directory
    output_dir = Path("outputs/hrrr")
    if output_dir.exists():
        # Recent processing
        recent_dirs = sorted([d for d in output_dir.iterdir() if d.is_dir()], 
                           key=lambda x: x.stat().st_mtime, reverse=True)[:5]
        
        status_table = Table(title="Recent Processing", box=box.ROUNDED)
        status_table.add_column("Date", style="cyan")
        status_table.add_column("Hours", style="green") 
        status_table.add_column("Size", style="yellow")
        status_table.add_column("Modified", style="magenta")
        
        for date_dir in recent_dirs:
            hours = [h.name for h in date_dir.iterdir() if h.is_dir()]
            size = sum(f.stat().st_size for f in date_dir.rglob('*') if f.is_file()) // (1024*1024)
            modified = datetime.fromtimestamp(date_dir.stat().st_mtime).strftime("%m-%d %H:%M")
            
            status_table.add_row(
                date_dir.name,
                f"{len(hours)} hours", 
                f"{size} MB",
                modified
            )
        
        console.print(status_table)
    else:
        console.print("[yellow]No outputs directory found.[/yellow]")
    
    # System resources
    console.print(f"\n[bold]💻 System Resources:[/bold]")
    console.print(f"CPU Cores: {mp.cpu_count()}")
    console.print(f"Current Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

@app.command("quick")
def quick_mode(
    workflow: str = typer.Argument(help="Workflow type: severe|fire|nowcast|heat|research|monitor"),
    date: Optional[str] = typer.Option(None, "--date", "-d", help="Date (YYYYMMDD)"),
    hour: Optional[int] = typer.Option(None, "--hour", "-h", help="Hour (0-23)"),
    workers: int = typer.Option(4, "--workers", "-w", help="Number of workers")
):
    """⚡ Quick workflow execution"""
    show_banner()
    
    workflows = {
        "severe": f"python processor_cli.py {date or 'latest'} {hour or ''} --categories severe,instability --hours 0-24 --workers {workers}",
        "fire": "python processor_cli.py --latest --categories smoke,fire --hours 0-6",
        "nowcast": "python processor_cli.py --latest --categories reflectivity,surface,severe --hours 0-3 --workers 4",
        "heat": f"python processor_cli.py {date or 'latest'} 12 --categories heat,surface --hours 0-48 --workers {workers}",
        "research": f"python processor_cli.py {date or 'latest'} 00 --hours 0-48 --workers {workers}",
        "monitor": "python monitor_continuous.py"
    }
    
    if workflow not in workflows:
        console.print(f"[red]Unknown workflow: {workflow}[/red]")
        console.print(f"Available: {', '.join(workflows.keys())}")
        return
    
    cmd = workflows[workflow].replace("latest ", "--latest ").split()
    console.print(f"[bold blue]Executing:[/bold blue] {' '.join(cmd)}")
    subprocess.run(cmd)

@app.command("status")
def status():
    """📊 Show system status"""
    show_banner()
    show_system_status()

@app.command("list")
def list_products():
    """📋 List available products and categories"""
    show_banner()
    
    # Create categories tree
    tree = Tree("🌪️ Available Categories & Parameters")
    
    for key, name in CATEGORIES.items():
        branch = tree.add(f"[bold]{name}[/bold]")
        # Add some example parameters (you could load these from actual config)
        if key == "severe":
            branch.add("🌪️ Significant Tornado Parameter (STP)")
            branch.add("🌀 Supercell Composite Parameter (SCP)")
            branch.add("⚡ Energy Helicity Index (EHI)")
        elif key == "smoke":
            branch.add("🔥 Near Surface Smoke")
            branch.add("👁️ Visibility (Smoke)")
            branch.add("📊 Fire Smoke Composite")
        # Add more as needed
    
    console.print(tree)

if __name__ == "__main__":
    app()