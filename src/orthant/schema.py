from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel


class ActionEnum(StrEnum):
    UPGRADE = "upgrade"
    DOWNGRADE = "downgrade"


class MigrationScriptMetadata(BaseModel):
    path: Path
    revision_id: str | None
    revises_id: str | None
