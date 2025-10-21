import tomllib
from pathlib import Path

from pydantic import BaseModel


class Config(BaseModel):
    versions_dir: Path
    version_index_file: Path
    template_file: Path
    env_file: Path
    readme_file: Path


def load_configs() -> Config:
    pyproject_file = Path("pyproject.toml")
    if not pyproject_file.exists():
        raise FileNotFoundError("Unable to locate configuration file.")

    with open(pyproject_file, "rb") as file:
        raw_orthant_config: dict = tomllib.load(file).get("tool", {}).get("orthant", {})

        raw_orthant_base_dir: str = raw_orthant_config.get("base_dir", "orthant")
        parsed_orthant_base_dir: Path = Path(raw_orthant_base_dir)

        parsed_orthant_versions_dir: Path = parsed_orthant_base_dir / "versions"
        parsed_orthant_version_index_file: Path = (
            parsed_orthant_base_dir / "VERSION_INDEX"
        )
        parsed_orthant_template_file: Path = parsed_orthant_base_dir / "script.py.mako"
        parsed_orthant_env_file: Path = parsed_orthant_base_dir / "env.py"
        parsed_orthant_readme_file: Path = parsed_orthant_base_dir / "README.md"

        return Config(
            versions_dir=parsed_orthant_versions_dir,
            version_index_file=parsed_orthant_version_index_file,
            template_file=parsed_orthant_template_file,
            env_file=parsed_orthant_env_file,
            readme_file=parsed_orthant_readme_file,
        )


configs = load_configs()
