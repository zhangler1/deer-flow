"""Skill system prompt injection for deer-flow-1.

Generates <skill_system> XML section for injection into researcher.md,
with simplified caching (threading.Lock + lru_cache, no async refresh thread).
Adapted from deer-flow2.0-harness/agents/lead_agent/prompt.py.
"""

import logging
import threading
from functools import lru_cache

from src.skills import load_skills
from src.skills.types import Skill

logger = logging.getLogger(__name__)

# Simplified cache: threading.Lock + cache variable + lru_cache
_skills_lock = threading.Lock()
_enabled_skills_cache: list[Skill] | None = None


def _load_enabled_skills_sync() -> list[Skill]:
    """Load enabled skills synchronously."""
    return list(load_skills(enabled_only=True))


def _get_enabled_skills() -> list[Skill]:
    """Get cached enabled skills, loading if necessary."""
    global _enabled_skills_cache

    with _skills_lock:
        if _enabled_skills_cache is not None:
            return list(_enabled_skills_cache)

    # Load skills outside the lock to avoid blocking
    try:
        skills = _load_enabled_skills_sync()
    except Exception:
        logger.exception("Failed to load enabled skills for prompt injection")
        skills = []

    with _skills_lock:
        # Double-check: another thread might have loaded while we were outside
        if _enabled_skills_cache is None:
            _enabled_skills_cache = skills
        return list(_enabled_skills_cache)


def _skill_mutability_label(category: str) -> str:
    """Return a label indicating if a skill is built-in or custom/editable."""
    return "[自定义，可编辑]" if category == "custom" else "[内置]"


@lru_cache(maxsize=32)
def _get_cached_skills_prompt_section(
    skill_signature: tuple[tuple[str, str, str, str], ...],
    available_skills_key: tuple[str, ...] | None,
) -> str:
    """Build the <skill_system> XML section with LRU caching.

    Args:
        skill_signature: Tuple of (name, description, category, location) for each skill.
        available_skills_key: Tuple of skill names to include, or None for all.

    Returns:
        Formatted skill_system XML string, or empty string if no skills to show.
    """
    filtered = [
        (name, description, category, location)
        for name, description, category, location in skill_signature
        if available_skills_key is None or name in available_skills_key
    ]

    if not filtered:
        return ""

    skill_items = "\n".join(
        f"    <skill>\n"
        f"        <name>{name}</name>\n"
        f"        <description>{description} {_skill_mutability_label(category)}</description>\n"
        f"        <location>{location}</location>\n"
        f"    </skill>"
        for name, description, category, location in filtered
    )
    skills_list = f"<available_skills>\n{skill_items}\n</available_skills>"

    return f"""<skill_system>
你可以访问技能（Skills），它们为特定任务提供优化的工作流程。每个技能包含最佳实践、分析框架和附加资源引用。

**渐进式加载模式：**
1. 当用户查询匹配某个技能的使用场景时，立即使用 `read_file` 读取该技能的主文件（路径见下方 skill 标签中的 location 属性）
2. 阅读并理解该技能的工作流程和指令
3. 技能文件中可能引用同目录下的其他资源文件
4. 仅在执行过程中需要时才加载引用的资源
5. 严格遵循技能中的指令执行

{skills_list}

</skill_system>"""


def get_skills_prompt_section(available_skills: set[str] | None = None) -> str:
    """Generate the skills prompt section for injection into researcher.md.

    Args:
        available_skills: Set of skill names to include, or None for all enabled skills.
                         Empty set means no skills.

    Returns:
        Formatted <skill_system> XML string, or empty string if no skills available.
    """
    skills = _get_enabled_skills()

    # No skills at all
    if not skills:
        return ""

    # available_skills is an empty set — no skills for this agent
    if available_skills is not None and not any(skill.name in available_skills for skill in skills):
        return ""

    # Build skill signature using host machine absolute paths
    skill_signature = tuple(
        (skill.name, skill.description, skill.category, skill.get_skill_file_path())
        for skill in skills
    )

    available_key = tuple(sorted(available_skills)) if available_skills is not None else None

    return _get_cached_skills_prompt_section(skill_signature, available_key)


def clear_skills_cache() -> None:
    """Clear the skills prompt cache, forcing reload on next access.

    Should be called after any skill CRUD operation.
    """
    global _enabled_skills_cache
    _get_cached_skills_prompt_section.cache_clear()
    with _skills_lock:
        _enabled_skills_cache = None


def refresh_skills_cache() -> None:
    """Force refresh the skills cache by reloading from disk."""
    clear_skills_cache()
    # Pre-load the cache
    _get_enabled_skills()
