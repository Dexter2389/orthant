import importlib.util

from click.exceptions import ClickException
from rich.console import Console

from .configs import configs


def ensure_env_file_exists(console: Console):
    if not configs.env_file.parent.exists() or not configs.env_file.exists():
        console.print(
            f"[bold red]Error: Directory '{configs.env_file.parent}' not initialized.[/bold red]"
        )
        raise ClickException("Please run the 'init' command first.")


def load_env_file_and_run_migration(migration_task_partial):
    try:
        module_spec = importlib.util.spec_from_file_location(
            configs.env_file.stem, configs.env_file
        )
        module = importlib.util.module_from_spec(module_spec)
        module_spec.loader.exec_module(module)

        module.run_migrations_online(migration_task_partial)

    except Exception:
        raise ClickException(f"Could not load 'env.py' at '{configs.env_file}'.")
