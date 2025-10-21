import importlib.util
import re
from datetime import UTC, datetime

from click.exceptions import ClickException
from mako.template import Template
from qdrant_client import QdrantClient
from rich.console import Console
from rich.table import Table

from .configs import configs
from .graph import build_migration_run_plan
from .schema import ActionEnum
from .templates import TEMPLATE_ENV_PY, TEMPLATE_README, TEMPLATE_SCRIPT_MAKO
from .utils import ensure_env_file_exists


def get_current_revision() -> str | None:
    if not configs.version_index_file.exists():
        return None

    with open(configs.version_index_file) as index_file:
        return index_file.read().strip() or None


def _set_current_revision(revision_id: str | None):
    configs.version_index_file.parent.mkdir(exist_ok=True, parents=True)
    with open(configs.version_index_file, "w") as index_file:
        index_file.write(revision_id or "")


def run_migration_task(
    console: Console,
    client: QdrantClient,
    target_revision: str,
    dry_run: bool = False,
    verbose: bool = False,
):
    current_revision = get_current_revision()

    migration_run_plan = build_migration_run_plan(
        console=console,
        target_revision=target_revision,
        current_revision=current_revision,
        verbose=verbose,
    )

    if len(migration_run_plan) == 0:
        console.print("[bold green]Database is already up-to-date.[/bold green]")
        return

    console.print(
        f"Migrating from '{current_revision if current_revision is not None else 'base'}' to '{target_revision}'"
    )

    table = Table()
    table.add_column("Action", style="cyan", no_wrap=True)
    table.add_column("Revision ID", style="magenta")
    for migration, action in migration_run_plan:
        match action:
            case ActionEnum.UPGRADE:
                action_style = "bold green"
            case ActionEnum.DOWNGRADE:
                action_style = "bold red"

        table.add_row(
            f"[{action_style}]{action.upper()}[/{action_style}]", migration.revision_id
        )

    console.print(table)

    if dry_run:
        console.print(
            "\n[bold yellow]Dry run successful. No changes were made.[/bold yellow]"
        )
        return

    console.print("\n[bold]Applying migrations...[/bold]")
    for migration, action in migration_run_plan:
        try:
            module_spec = importlib.util.spec_from_file_location(
                migration.path.stem, migration.path
            )
            module = importlib.util.module_from_spec(module_spec)
            module_spec.loader.exec_module(module)

            action_function = getattr(module, action)

            with console.status(
                f"[bold cyan]Running {action.upper()} for {migration.revision_id}...[/bold cyan]"
            ):
                action_function(client)

            match action:
                case ActionEnum.UPGRADE:
                    _set_current_revision(migration.revision_id)
                case ActionEnum.DOWNGRADE:
                    _set_current_revision(migration.revises_id)

            if verbose:
                console.print(f"[gray50]Done: {migration.revision_id}[/gray50]")

        except (ImportError, AttributeError) as error:
            raise ClickException(
                f"Invalid migration script '{migration.path.name}': {error}"
            )
        except Exception:
            if verbose:
                console.print_exception(show_locals=True)

            raise ClickException(
                f"[bold red]An error occurred during execution of '{migration.revision_id}'. Aborting migration.[/bold red]"
            )

    console.print("[bold green]Migration finished successfully.[/bold green]")


def create_new_migration(
    console: Console,
    short_description: str,
    long_description: None | str,
    verbose: bool = False,
):
    ensure_env_file_exists(console=console)

    current_head = get_current_revision()
    if current_head is None:
        path = build_migration_run_plan(
            console=console,
            target_revision="head",
            current_revision=None,
            verbose=verbose,
        )
        current_head = path[-1][0].revision_id if path else None

    revises_id = current_head or ""

    new_revision_id = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    sanitized_short_description = (
        re.sub(r"[\s\W]+", "_", short_description).lower().strip("_")
    )

    migration_file_path = (
        configs.versions_dir
        / f"{new_revision_id}_{sanitized_short_description[:39].strip('_')}.py"
    )

    try:
        if not configs.template_file.exists():
            raise ClickException(
                f"Template file not found at '{configs.template_file}'"
            )

        template = Template(filename=str(configs.template_file))  # noqa: S702
        rendered_migration_script = template.render(
            revision=new_revision_id,
            revises=revises_id,
            created_at=datetime.now(UTC).isoformat(),
            description=short_description
            + ("\n\n" + long_description if long_description else ""),
        )
        with open(migration_file_path, "w") as file:
            file.write(rendered_migration_script)

        console.print("[bold green]Created new migration file.[/bold green]")

    except Exception as error:
        raise ClickException(f"Failed to create new migration file. {error}")


def initialize_orthant_env(console: Console, verbose: bool = False):
    if not configs.versions_dir.exists():
        configs.versions_dir.mkdir(parents=True, exist_ok=True)

        if verbose:
            console.print(f"[green]Created '{configs.versions_dir}'.[/green]")
    else:
        if verbose:
            console.print(f"[yellow]'{configs.versions_dir}' already exists.[/yellow]")

    if not configs.env_file.exists():
        with open(configs.env_file, "w") as env_file:
            env_file.write(TEMPLATE_ENV_PY)

        if verbose:
            console.print(f"[green]Created '{configs.env_file}'.[/green]")
    else:
        if verbose:
            console.print(f"[yellow]'{configs.env_file}' already exists.[/yellow]")

    if not configs.template_file.exists():
        with open(configs.template_file, "w") as template_file:
            template_file.write(TEMPLATE_SCRIPT_MAKO)

        if verbose:
            console.print(f"[green]Created '{configs.template_file}'.[/green]")
    else:
        if verbose:
            console.print(f"[yellow]'{configs.template_file}' already exists.[/yellow]")

    if not configs.readme_file.exists():
        with open(configs.readme_file, "w") as readme_file:
            readme_file.write(TEMPLATE_README)

        if verbose:
            console.print(f"[green]Created '{configs.readme_file}'.[/green]")
    else:
        if verbose:
            console.print(f"[yellow]'{configs.readme_file}' already exists.[/yellow]")

    console.print(
        f"[bold green]Successfully initialized Orthant at '{configs.version_index_file.parent}'.[/bold green]"
    )
    console.print(
        "Next steps: Edit [bold]env.py[/bold] to configure your Qdrant connection."
    )
