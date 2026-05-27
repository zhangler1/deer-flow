"""Skill loader for deer-flow-1.

Scans skills/public/ and skills/custom/ directories for SKILL.md files,
parses frontmatter, and builds Skill objects.
Adapted from deer-flow2.0-harness, with path adjustments for deer-flow-1's src/ layout.
"""

import logging
import os
from pathlib import Path

from .parser import parse_skill_file
from .types import Skill

logger = logging.getLogger(__name__)


def get_skills_root_path() -> Path:
    """Get the root path of the skills directory.

    Returns:
        Path to the skills directory (deer-flow-1/skills)
    """
    # loader.py lives at src/skills/loader.py — 2 parents up reaches project root
    project_root = Path(__file__).resolve().parents[2]
    skills_dir = project_root / "skills"
    return skills_dir


def load_skills(skills_path: Path | None = None, use_config: bool = True, enabled_only: bool = False) -> list[Skill]:
    """Load all skills from the skills directory.

    Scans both public and custom skill directories, parsing SKILL.md files
    to extract metadata. The enabled state is determined by conf.yaml.

    Args:
        skills_path: Optional custom path to skills directory.
                     If not provided and use_config is True, uses path from config.
                     Otherwise defaults to deer-flow-1/skills
        use_config: Whether to load skills path from config (default: True)
        enabled_only: If True, only return enabled skills (default: False)

    Returns:
        List of Skill objects, sorted by name
    """
    if skills_path is None:
        if use_config:
            try:
                from src.config import get_skills_config

                skills_config = get_skills_config()
                skills_path = skills_config.get_skills_path()
            except Exception:
                # Fallback to default if config fails
                skills_path = get_skills_root_path()
        else:
            skills_path = get_skills_root_path()

    if not skills_path.exists():
        return []

    skills_by_name: dict[str, Skill] = {}

    # Scan public and custom directories
    for category in ["public", "custom"]:
        category_path = skills_path / category
        if not category_path.exists() or not category_path.is_dir():
            continue

        for current_root, dir_names, file_names in os.walk(category_path, followlinks=True):
            # Keep traversal deterministic and skip hidden directories.
            dir_names[:] = sorted(name for name in dir_names if not name.startswith("."))
            if "SKILL.md" not in file_names:
                continue

            skill_file = Path(current_root) / "SKILL.md"
            relative_path = skill_file.parent.relative_to(category_path)

            skill = parse_skill_file(skill_file, category=category, relative_path=relative_path)
            if skill:
                skills_by_name[skill.name] = skill

    skills = list(skills_by_name.values())

    # Load skills enabled/disabled state from conf.yaml
    try:
        from src.config import get_skills_config

        skills_config = get_skills_config()
        enabled_map = skills_config.get_enabled_map()
        for skill in skills:
            if skill.name in enabled_map:
                skill.enabled = enabled_map[skill.name]
            else:
                skill.enabled = True  # Default to enabled if not specified
    except Exception as e:
        # If config loading fails, default to all enabled
        logger.warning("Failed to load skills config: %s", e)

    # Filter by enabled status if requested
    if enabled_only:
        skills = [skill for skill in skills if skill.enabled]

    # Sort by name for consistent ordering
    skills.sort(key=lambda s: s.name)

    return skills
