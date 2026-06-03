# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
通用引用规则加载器

统一加载 reporter_ref_rules.md 和 researcher_ref_rules.md，
按 <!-- SECTION: {角色}_ref_{section} --> 标记解析，暴露对应常量。

所有规则修改只需编辑对应的 .md 文件，无需改动 Python 代码。
"""

import os
import re


def _load_sections(filename: str) -> dict[str, str]:
    """从指定 .md 文件中解析以 <!-- SECTION: xxx --> 标记分隔的段落。"""
    filepath = os.path.join(os.path.dirname(__file__), filename)
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    sections: dict[str, str] = {}
    pattern = r'<!-- SECTION: (\w+) -->\s*\n(.*?)(?=<!-- SECTION:|\Z)'
    for match in re.finditer(pattern, content, re.DOTALL):
        sections[match.group(1)] = match.group(2).strip()

    return sections


# ─── Reporter 规则 ───
_reporter = _load_sections("reporter_ref_rules.md")

REPORTER_RULES: str = _reporter.get("reporter_ref_rules", "")
REPORTER_REMINDER: str = _reporter.get("reporter_ref_reminder", "")

# ─── Researcher 规则 ───
_researcher = _load_sections("researcher_ref_rules.md")

RESEARCHER_RULES: str = _researcher.get("researcher_ref_rules", "")
RESEARCHER_REMINDER: str = _researcher.get("researcher_ref_reminder", "")
