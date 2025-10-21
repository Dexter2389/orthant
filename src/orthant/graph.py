import re
from graphlib import CycleError, TopologicalSorter
from pathlib import Path

from click.exceptions import ClickException
from rich.console import Console

from .configs import configs
from .schema import ActionEnum, MigrationScriptMetadata


def _get_migration_scripts() -> list[Path]:
    if not configs.versions_dir.exists():
        return []

    return [
        file
        for file in configs.versions_dir.iterdir()
        if file.is_file() and file.suffix == ".py"
    ]


def _parse_migration_script_headers(script_path: Path) -> MigrationScriptMetadata:
    with open(script_path) as file:
        content = file.read()

    revision_id_match = re.search(r"Revision ID:\s*(\w+)", content)
    revises_id_match = re.search(r"Revises:[^\S\n]*(\w*)", content)

    return MigrationScriptMetadata(
        path=script_path,
        revision_id=revision_id_match.group(1) if revision_id_match else None,
        revises_id=revises_id_match.group(1)
        if revises_id_match and revises_id_match.group(1)
        else None,
    )


def build_migration_run_plan(
    console: Console,
    target_revision: str,
    current_revision: str | None,
    verbose: bool = False,
) -> list[tuple[MigrationScriptMetadata, ActionEnum]]:
    migration_metadata = [
        _parse_migration_script_headers(script) for script in _get_migration_scripts()
    ]
    revision_id_to_metadata_mapping = {
        metadata.revision_id: metadata
        for metadata in migration_metadata
        if metadata.revision_id is not None
    }

    graph = {
        metadata.revision_id: {metadata.revises_id}
        if metadata.revises_id is not None
        else set()
        for metadata in migration_metadata
        if metadata.revision_id is not None
    }

    try:
        ts = TopologicalSorter(graph)
        full_ordered_path = list(ts.static_order())
    except CycleError as error:
        console.print("[bold red]Error: A circular dependency was detected![/bold red]")
        console.print(f"Cycle path: {' -> '.join(error.args[1])}")
        raise ClickException("Circular dependency detected in the migration history.")

    relative_match = re.match(r"^(HEAD)~(\d+)$", target_revision.upper())
    if relative_match:
        base_revision_name, number_of_steps_back = relative_match.groups()
        target_index = len(full_ordered_path) - int(number_of_steps_back)
        target_revision = (
            full_ordered_path[target_index - 1] if target_index > 0 else "base"
        )
        if verbose:
            console.print(
                f"Resolved '{relative_match.group(0)}' to target revision '{target_revision}'"
            )

    try:
        current_index = (
            full_ordered_path.index(current_revision) + 1
            if current_revision is not None
            else 0
        )
    except ValueError:
        raise ClickException(
            f"Current revision '{current_revision}' not found in migration history."
        )

    if target_revision == "head":
        target_index = len(full_ordered_path)
    elif target_revision == "base":
        target_index = 0
    else:
        try:
            target_index = full_ordered_path.index(target_revision) + 1
        except ValueError:
            raise ClickException(
                f"Target revision '{target_revision}' not found in migration history."
            )

    if target_index > current_index:
        migrations_to_run = [
            (revision_id_to_metadata_mapping[revision_id], ActionEnum.UPGRADE)
            for revision_id in full_ordered_path[current_index:target_index]
        ]
    elif target_index < current_index:
        migrations_to_run = [
            (revision_id_to_metadata_mapping[revision_id], ActionEnum.DOWNGRADE)
            for revision_id in reversed(full_ordered_path[target_index:current_index])
        ]
    else:
        migrations_to_run = []

    if verbose:
        console.print(
            f"[bold blue]Migration run plan created for '{current_revision}' -> '{target_revision}'[/bold blue]"
        )

    return migrations_to_run
