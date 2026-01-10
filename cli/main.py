"""CLI interface for the coding agent."""

import asyncio
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel
from rich.markdown import Markdown

from agent.config import AgentConfig, get_config
from agent.models import Task
from agent.orchestrator import AgentOrchestrator

app = typer.Typer(help="Coding Agent - AI-powered coding assistant")
console = Console()


@app.command()
def run(
    task: str = typer.Argument(..., help="Task description"),
    workspace: Optional[str] = typer.Option(
        None, "--workspace", "-w", help="Workspace path (default: current directory)"
    ),
    model: Optional[str] = typer.Option(
        None, "--model", "-m", help="LLM model to use"
    ),
    provider: Optional[str] = typer.Option(
        None, "--provider", "-p", help="LLM provider (openai or ollama)"
    ),
) -> None:
    """
    Run the coding agent on a task.

    Example:
        coding-agent run "Add a login feature to the web app"
    """
    workspace_path = workspace or os.getcwd()

    console.print(
        Panel.fit(
            f"[bold blue]Coding Agent[/bold blue]\n"
            f"Task: {task}\n"
            f"Workspace: {workspace_path}",
            border_style="blue",
        )
    )

    # Load configuration
    config = get_config()
    if provider:
        config.default_llm_provider = provider
    if model:
        if provider == "openai":
            config.openai_model = model
        elif provider == "ollama":
            config.ollama_model = model

    # Create task
    task_obj = Task(
        id=f"task_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        description=task,
        workspace_path=workspace_path,
        created_at=datetime.now().isoformat(),
    )

    # Run agent
    try:
        with console.status("[bold green]Initializing agent...") as status:
            orchestrator = AgentOrchestrator(config, workspace_path)

        # Run with progress
        result = asyncio.run(orchestrator.run(task_obj))

        # Display results
        if result["status"] == "completed":
            console.print("\n[bold green]✓ Task completed successfully![/bold green]")
        else:
            console.print(f"\n[bold yellow]Task ended: {result.get('status')}[/bold yellow]")

        console.print(f"\nIterations: {result['iterations']}")

        if result.get("verification_result"):
            vr = result["verification_result"]
            console.print(f"Quality Score: {vr.get('quality_score', 0):.2f}")

            if vr.get("issues"):
                console.print("\n[bold red]Issues:[/bold red]")
                for issue in vr["issues"]:
                    console.print(f"  - {issue}")

            if vr.get("suggestions"):
                console.print("\n[bold blue]Suggestions:[/bold blue]")
                for suggestion in vr["suggestions"]:
                    console.print(f"  - {suggestion}")

    except KeyboardInterrupt:
        console.print("\n[bold red]Interrupted by user[/bold red]")
    except Exception as e:
        console.print(f"\n[bold red]Error: {e}[/bold red]")
        raise typer.Exit(1)


@app.command()
def index(
    workspace: Optional[str] = typer.Option(
        None, "--workspace", "-w", help="Workspace path (default: current directory)"
    ),
    extensions: Optional[str] = typer.Option(
        None, "--extensions", "-e", help="File extensions to index (comma-separated)"
    ),
) -> None:
    """
    Index the workspace for semantic search.

    Example:
        coding-agent index --extensions ".py,.js,.ts"
    """
    workspace_path = workspace or os.getcwd()

    console.print(f"[bold blue]Indexing workspace:[/bold blue] {workspace_path}")

    config = get_config()
    orchestrator = AgentOrchestrator(config, workspace_path)

    # Parse extensions
    ext_list = None
    if extensions:
        ext_list = [ext.strip() for ext in extensions.split(",")]

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Indexing codebase...", total=None)

        try:
            num_chunks = asyncio.run(
                orchestrator.semantic_search.index_codebase(ext_list)
            )
            progress.update(task, completed=True)
            console.print(f"\n[bold green]✓ Indexed {num_chunks} code chunks[/bold green]")

        except Exception as e:
            console.print(f"\n[bold red]Error indexing: {e}[/bold red]")
            raise typer.Exit(1)


@app.command()
def config_show() -> None:
    """Show current configuration."""
    config = get_config()

    console.print(Panel.fit("[bold blue]Configuration[/bold blue]", border_style="blue"))
    console.print(f"\n[bold]LLM Provider:[/bold] {config.default_llm_provider}")
    console.print(f"[bold]OpenAI Model:[/bold] {config.openai_model}")
    console.print(f"[bold]Ollama Model:[/bold] {config.ollama_model}")
    console.print(f"[bold]Max Iterations:[/bold] {config.max_iterations}")
    console.print(f"[bold]Context Window Size:[/bold] {config.context_window_size}")
    console.print(f"[bold]Chroma DB Path:[/bold] {config.chroma_persist_directory}")


@app.command()
def config_set(
    key: str = typer.Argument(..., help="Configuration key"),
    value: str = typer.Argument(..., help="Configuration value"),
) -> None:
    """
    Set configuration value.

    Example:
        coding-agent config-set default_llm_provider ollama
    """
    # Note: This would need to write to .env file
    # For now, just show what would be set
    console.print(f"[bold green]Would set {key} = {value}[/bold green]")
    console.print(
        "[yellow]Note: Edit .env file directly to persist changes[/yellow]"
    )


@app.command()
def interactive() -> None:
    """
    Start interactive mode.

    In interactive mode, you can have a conversation with the agent.
    """
    workspace_path = os.getcwd()

    console.print(
        Panel.fit(
            "[bold blue]Coding Agent - Interactive Mode[/bold blue]\n"
            f"Workspace: {workspace_path}\n"
            "Type 'exit' or 'quit' to exit",
            border_style="blue",
        )
    )

    config = get_config()
    orchestrator = AgentOrchestrator(config, workspace_path)

    while True:
        try:
            # Get user input
            task_input = console.input("\n[bold green]You:[/bold green] ")

            if task_input.lower() in ["exit", "quit", "q"]:
                console.print("[bold blue]Goodbye![/bold blue]")
                break

            if not task_input.strip():
                continue

            # Create and run task
            task_obj = Task(
                id=f"task_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                description=task_input,
                workspace_path=workspace_path,
                created_at=datetime.now().isoformat(),
            )

            result = asyncio.run(orchestrator.run(task_obj))

            if result["status"] == "completed":
                console.print("[bold green]✓ Done[/bold green]")
            else:
                console.print(f"[yellow]{result.get('status')}[/yellow]")

        except KeyboardInterrupt:
            console.print("\n[bold blue]Use 'exit' to quit[/bold blue]")
        except Exception as e:
            console.print(f"[bold red]Error: {e}[/bold red]")


@app.command()
def version() -> None:
    """Show version information."""
    from agent import __version__

    console.print(f"[bold blue]Coding Agent v{__version__}[/bold blue]")


if __name__ == "__main__":
    app()

