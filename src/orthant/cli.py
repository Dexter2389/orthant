from functools import partial

import click
from rich.console import Console

from . import __version__
from .commands import (
    create_new_migration,
    get_current_revision,
    initialize_orthant_env,
    run_migration_task,
)
from .utils import ensure_env_file_exists, load_env_file_and_run_migration


@click.group()
def main() -> None:
    pass


@main.command()
def version() -> None:
    console = Console()
    console.print(f"Orthant CLI version: [green]{__version__}[/green]")


@main.command()
@click.option(
    "-m",
    "--message",
    required=True,
    multiple=True,
    help="Migration message. The first is the subject, subsequent are the body.",
)
@click.option("--verbose", is_flag=True, help="Enable verbose mode to echo steps.")
def new(message: tuple[str, ...], verbose: bool) -> None:
    console = Console()

    short_description = message[0]
    long_description = "\n".join(message[1:]) if len(message) > 1 else ""

    create_new_migration(
        console=console,
        short_description=short_description,
        long_description=long_description,
        verbose=verbose,
    )


@main.command()
@click.option("--verbose", is_flag=True, help="Enable verbose mode to echo steps.")
def init(verbose: bool) -> None:
    console = Console()

    initialize_orthant_env(console=console, verbose=verbose)


@main.command()
def current() -> None:
    console = Console()

    ensure_env_file_exists(console=console)

    current_revision = get_current_revision()
    if current_revision is not None:
        console.print(f"Current Revision: [bold cyan]{current_revision}[/bold cyan]")
    else:
        console.print(
            "Database is at [bold cyan]'base'[/bold cyan] (no migrations applied)."
        )


@main.command()
@click.argument("revision", nargs=1, default="head", type=click.STRING)
@click.option("--dry-run", is_flag=True, help="Simulate the migration.")
@click.option("--verbose", is_flag=True, help="Enable verbose mode to echo steps.")
def upgrade(revision: str, dry_run: bool, verbose: bool) -> None:
    console = Console()

    ensure_env_file_exists(console=console)

    task = partial(
        run_migration_task,
        console=console,
        target_revision=revision,
        dry_run=dry_run,
        verbose=verbose,
    )
    load_env_file_and_run_migration(task)


@main.command()
@click.argument("revision", nargs=1, default="HEAD~1", type=click.STRING)
@click.option("--dry-run", is_flag=True, help="Simulate the migration.")
@click.option("--verbose", is_flag=True, help="Enable verbose mode to echo steps.")
def downgrade(revision: str, dry_run: bool, verbose: bool) -> None:
    console = Console()

    ensure_env_file_exists(console=console)

    task = partial(
        run_migration_task,
        console=console,
        target_revision=revision,
        dry_run=dry_run,
        verbose=verbose,
    )
    load_env_file_and_run_migration(task)
