"""Skill data model for deer-flow-1.

Adapted from deer-flow2.0-harness, using host machine absolute paths
instead of container virtual paths (/mnt/skills).
"""

from dataclasses import dataclass
from pathlib import Path


@dataclass
class Skill:
    """Represents a skill with its metadata and file path."""

    name: str
    description: str
    license: str | None
    skill_dir: Path
    skill_file: Path
    relative_path: Path  # Relative path from category root to skill directory
    category: str  # 'public' or 'custom'
    enabled: bool = False  # Whether this skill is enabled

    @property
    def skill_path(self) -> str:
        """Returns the relative path from the category root (skills/{category}) to this skill's directory."""
        path = self.relative_path.as_posix()
        return "" if path == "." else path

    def get_skill_file_path(self) -> str:
        """Get the absolute path to this skill's SKILL.md file on the host machine.

        deer-flow-1 has no sandbox, so Agent's read_file tool can use this path directly.

        Returns:
            Absolute host path to the skill's SKILL.md file
        """
        return str(self.skill_file.resolve())

    def __repr__(self) -> str:
        return f"Skill(name={self.name!r}, description={self.description!r}, category={self.category!r})"
