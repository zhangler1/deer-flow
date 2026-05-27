"""Skills configuration for deer-flow-1.

Provides SkillsConfig Pydantic model for skill path and enabled state management.
Configuration is read from conf.yaml's 'skills' section.
"""

import os
import threading
from pathlib import Path
from typing import Optional

from pydantic import BaseModel

# Singleton instance with thread-safe access
_instance: Optional["SkillsConfig"] = None
_lock = threading.Lock()


class SkillsConfig(BaseModel):
    """Configuration for the skills system.

    Attributes:
        path: Optional absolute path to the skills directory.
              If not set, defaults to <project_root>/skills/
        enabled_skills: Dict mapping skill names to their enabled state.
                       Skills not in this dict default to enabled.
    """

    path: Optional[str] = None
    enabled_skills: dict[str, bool] = {}

    def get_skills_path(self) -> Path:
        """Get the absolute path to the skills directory.

        Returns:
            Path to the skills directory. Uses configured path if set,
            otherwise defaults to <project_root>/skills/
        """
        if self.path:
            return Path(self.path)
        # Default: project_root/skills/
        # skills_config.py lives at src/config/skills_config.py — 2 parents up reaches project root
        project_root = Path(__file__).resolve().parents[2]
        return project_root / "skills"

    def get_enabled_map(self) -> dict[str, bool]:
        """Get the enabled/disabled mapping for skills.

        Returns:
            Dict mapping skill names to their enabled state.
        """
        return self.enabled_skills

    def is_skill_enabled(self, skill_name: str) -> bool:
        """Check if a specific skill is enabled.

        Args:
            skill_name: Name of the skill to check.

        Returns:
            True if the skill is enabled (default), False if explicitly disabled.
        """
        return self.enabled_skills.get(skill_name, True)


def get_skills_config() -> SkillsConfig:
    """Get the global SkillsConfig instance (singleton).

    Returns:
        The cached SkillsConfig instance.
    """
    global _instance
    if _instance is not None:
        return _instance

    with _lock:
        if _instance is not None:
            return _instance
        _instance = _load_skills_config_from_yaml()
        return _instance


def set_skills_config(config: SkillsConfig) -> None:
    """Set the global SkillsConfig instance (for testing or manual override).

    Args:
        config: The SkillsConfig instance to use.
    """
    global _instance
    with _lock:
        _instance = config


def _load_skills_config_from_yaml() -> SkillsConfig:
    """Load SkillsConfig from conf.yaml's 'skills' section."""
    try:
        from src.config import load_yaml_config

        config_path = os.path.join(os.getcwd(), "conf.yaml")
        config = load_yaml_config(config_path)
        skills_section = config.get("SKILLS", {}) or {}

        # Extract path
        path = skills_section.get("path")

        # Extract enabled_skills mapping
        enabled_skills = {}
        skills_list = skills_section.get("enabled_skills", {})
        if isinstance(skills_list, dict):
            for name, state in skills_list.items():
                if isinstance(state, dict):
                    enabled_skills[name] = state.get("enabled", True)
                elif isinstance(state, bool):
                    enabled_skills[name] = state

        return SkillsConfig(path=path, enabled_skills=enabled_skills)
    except Exception:
        # If config loading fails, use defaults
        return SkillsConfig()


def reset_skills_config() -> None:
    """Reset the cached SkillsConfig instance, forcing reload on next access."""
    global _instance
    with _lock:
        _instance = None
