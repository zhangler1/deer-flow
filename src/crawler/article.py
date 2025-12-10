# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import re
from typing import Optional
from urllib.parse import urljoin

from markdownify import markdownify as md


class Article:
    url: str

    def __init__(self, title: str, html_content: str, markdown_content: Optional[str] = None):
        self.title = title
        self.html_content = html_content
        self._cached_markdown = markdown_content  # 缓存的Markdown内容，避免重复转换

    def to_markdown(self, including_title: bool = True) -> str:
        # 如果已有缓存的Markdown，直接使用
        if self._cached_markdown is not None:
            if including_title:
                return f"# {self.title}\n\n{self._cached_markdown}"
            return self._cached_markdown
        
        # 否则使用markdownify转换
        markdown = ""
        if including_title:
            markdown += f"# {self.title}\n\n"
        markdown += md(self.html_content)
        return markdown

    def to_message(self) -> list[dict]:
        image_pattern = r"!\[.*?\]\((.*?)\)"

        content: list[dict] = []
        parts = re.split(image_pattern, self.to_markdown())

        for i, part in enumerate(parts):
            if i % 2 == 1:
                image_url = urljoin(self.url, part.strip())
                content.append({"type": "image_url", "image_url": {"url": image_url}})
            else:
                content.append({"type": "text", "text": part.strip()})

        return content
