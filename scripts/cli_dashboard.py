#!/usr/bin/env python3
"""
Terminal-based Dashboard for REMAININGCONNECTIONS.

Provides a rich, interactive view of the project's data directly from the command line.
Features include:
- Real-time proxy statistics visualization.
- Protocol distribution charts (ASCII).
- Latency heatmaps.
- Export options for raw data.
- System health overview.

Dependencies:
    pip install rich tabulate
"""

import json
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.text import Text
    from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn
    from rich.layout import Layout
    from rich.tree import Tree
    import tabulate
except ImportError:
    print("Missing dependencies. Please install them:")
    print("pip install rich tabulate")
    sys.exit(1)

console = Console()


class ColorScheme:
    """Define colors for different statuses."""
    WORKING = "#2ecc71"      # Green
    UNVERIFIED = "#f1c40f"   # Yellow
    FAILED = "#e74c3c"       # Red
    INFO = "#3498db"         # Blue
    BOLD = "bold"


class TerminalDashboard:
    """Main class for rendering the dashboard."""

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.proxies_file = self.data_dir / "tg_proxies_found.json"
        self.subscriptions_file = self.data_dir / "subscriptions_found.json"
        
    def load_data(self):
        """Load proxies and subscriptions from JSON files."""
        proxies = []
        subs = []
        
        if self.proxies_file.exists():
            try:
                with open(self.proxies_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                proxies = data.get('proxies', [])
            except Exception as e:
                console.print(f"[red]Error loading proxies: {e}[/red]")
        else:
            console.print("[yellow]No proxies found.[/yellow]")

        if self.subscriptions_file.exists():
            try:
                with open(self.subscriptions_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                subs = data.get('subscriptions', [])
            except Exception as e:
                console.print(f"[red]Error loading subscriptions: {e}[/red]")
        
        return proxies, subs

    def render_header(self):
        """Render the dashboard header."""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        title = "[bold cyan]REMAININGCONNECTIONS[/bold cyan] | [bold white]Live Dashboard[/bold white]"
        time_str = f"[dim]Updated: {now}[/dim]"
        
        header = Panel(
            f"{title}\n{time_str}",
            border_style="blue",
            padding=(1, 2)
        )
        console.print(header)

    def render_stats_summary(self, proxies: List[Dict], subs: List[Dict]):
        """Render high-level statistics."""
        total_p = len(proxies)
        working_p = sum(1 for p in proxies if p.get('status') == 'working')
        rate_p = (working_p / total_p * 100) if total_p > 0 else 0
        
        total_s = len(subs)
        working_s = sum(1 for s in subs if s.get('status') == 'working')
        
        table = Table(title="[bold]System Overview[/bold]", show_header=True, header_style="bold magenta")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", justify="right", style="white")
        
        table.add_row("Total Proxies", str(total_p))
        table.add_row("Working Proxies", f"[green]{working_p}[/green]")
        table.add_row("Success Rate", f"{rate_p:.1f}%")
        table.add_row("Subscriptions", str(total_s))
        table.add_row("Active Subs", f"[green]{working_s}[/green]")
        
        console.print(table)

    def render_protocol_distribution(self, proxies: List[Dict]):
        """Render protocol usage chart."""
        protocols = {}
        for p in proxies:
            proto = p.get('protocol', 'unknown').upper()
            protocols[proto] = protocols.get(proto, 0) + 1
            
        if not protocols:
            console.print("[yellow]No protocol data available.[/yellow]")
            return

        # Sort by count
        sorted_protos = sorted(protocols.items(), key=lambda x: x[1], reverse=True)
        
        table = Table(title="[bold]Protocol Distribution[/bold]")
        table.add_column("Protocol", style="cyan")
        table.add_column("Count", justify="right")
        table.add_column("Bar", width=30)
        
        max_count = sorted_protos[0][1] if sorted_protos else 1
        
        for proto, count in sorted_protos[:10]:  # Top 10
            bar_len = int((count / max_count) * 30)
            bar = "█" * bar_len
            table.add_row(proto, str(count), f"[blue]{bar}[/blue]")
            
        console.print(table)

    def render_latency_stats(self, proxies: List[Dict]):
        """Render latency statistics."""
        latencies = [p['latency_ms'] for p in proxies if p.get('latency_ms') is not None]
        
        if not latencies:
            console.print("[yellow]No latency data available.[/yellow]")
            return
            
        avg_lat = sum(latencies) / len(latencies)
        min_lat = min(latencies)
        max_lat = max(latencies)
        
        # Categorize
        fast = sum(1 for l in latencies if l < 100)
        medium = sum(1 for l in latencies if 100 <= l < 300)
        slow = sum(1 for l in latencies if l >= 300)
        
        table = Table(title="[bold]Performance Metrics[/bold]")
        table.add_column("Category", style="cyan")
        table.add_column("Latency (ms)", justify="right")
        table.add_column("Count", justify="right")
        
        table.add_row("Average", f"{avg_lat:.0f}", "-")
        table.add_row("Minimum", f"{min_lat:.0f}", "-")
        table.add_row("Maximum", f"{max_lat:.0f}", "-")
        table.add_row("---", "---", "---")
        table.add_row("Fast (<100ms)", "<100", str(fast))
        table.add_row("Medium (100-300ms)", "100-300", str(medium))
        table.add_row("Slow (>300ms)", ">300", str(slow))
        
        console.print(table)

    def render_top_proxies(self, proxies: List[Dict]):
        """Render top 5 working proxies."""
        working = [p for p in proxies if p.get('status') == 'working']
        # Sort by latency
        working.sort(key=lambda x: x.get('latency_ms') or float('inf'))
        top_5 = working[:5]
        
        if not top_5:
            console.print("[yellow]No working proxies found.[/yellow]")
            return
            
        table = Table(title="[bold]Top 5 Working Proxies[/bold]")
        table.add_column("Rank", style="dim")
        table.add_column("Protocol", style="cyan")
        table.add_column("Server", style="white")
        table.add_column("Port", justify="right")
        table.add_column("Latency", justify="right")
        
        for i, p in enumerate(top_5, 1):
            server = p.get('server', 'N/A')
            port = p.get('port', '?')
            proto = p.get('protocol', '?').upper()
            lat = p.get('latency_ms', '?')
            
            # Truncate server for display
            if len(server) > 20:
                server = server[:17] + "..."
                
            table.add_row(str(i), proto, server, str(port), f"{lat} ms")
            
        console.print(table)

    def run(self):
        """Execute the dashboard rendering sequence."""
        console.clear()
        self.render_header()
        
        proxies, subs = self.load_data()
        
        with Progress(SpinnerColumn(), TextColumn("[bold blue]Loading data...[/bold blue]")) as progress:
            task = progress.add_task("", total=None)
            # Simulate slight delay for effect
            import time
            time.sleep(0.5)
            progress.update(task, completed=100)
            
        self.render_stats_summary(proxies, subs)
        self.render_protocol_distribution(proxies)
        self.render_latency_stats(proxies)
        self.render_top_proxies(proxies)
        
        console.print("\n[dim]Press Ctrl+C to exit[/dim]")


def main():
    """CLI Entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", default="data", help="Path to data directory")
    
    args = parser.parse_args()
    
    dashboard = TerminalDashboard(data_dir=args.data_dir)
    dashboard.run()


if __name__ == "__main__":
    main()