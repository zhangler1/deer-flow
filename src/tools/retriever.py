# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import logging
from typing import List, Optional, Type

from langchain_core.callbacks import (
    AsyncCallbackManagerForToolRun,
    CallbackManagerForToolRun,
)
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from src.config.tools import SELECTED_RAG_PROVIDER
from src.rag import Document, Resource, Retriever, build_retriever
from src.utils.enhanced_logger import console_print

logger = logging.getLogger(__name__)


class RetrieverInput(BaseModel):
    keywords: str = Field(description="search keywords to look up")


class RetrieverTool(BaseTool):
    name: str = "local_search_tool"
    description: str = "Useful for retrieving information from the file with `rag://` uri prefix, it should be higher priority than the web search or writing code. Input should be a search keywords."
    args_schema: Type[BaseModel] = RetrieverInput

    retriever: Retriever = Field(default_factory=Retriever)
    resources: list[Resource] = Field(default_factory=list)

    def _run(
        self,
        keywords: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str | list[dict]:
        logger.info(
            f"Retriever tool query: {keywords}", extra={"resources": self.resources}
        )
        documents = self.retriever.query_relevant_documents(keywords, self.resources)
        if not documents:
            return "No results found from the local knowledge base."
        
        # 打印检索结果摘要（带日志级别判断）
        console_print(
            f"\033[32m[本地检索摘要] 关键词: '{keywords}'\033[0m \033[35m| 返回结果数: {len(documents)} 条\033[0m",
            level=logging.INFO
        )
        if documents:
            console_print(
                f"\033[32m[结果详情] 共{len(documents)}条结果:\033[0m",
                level=logging.DEBUG
            )
            for i, doc in enumerate(documents):
                title = doc.title if doc.title else '无标题'
                # 获取内容（将chunks拼接）
                content = "\n\n".join([chunk.content for chunk in doc.chunks]) if doc.chunks else ''
                # 截取内容前40字
                content_preview = content[:40] if content else '无内容'
                console_print(
                    f"\033[32m  {i+1}. 标题: {title}\033[0m",
                    level=logging.DEBUG
                )
                console_print(
                    f"\033[35m     内容: {content_preview}...\033[0m",
                    level=logging.DEBUG
                )
        
        return [doc.to_dict() for doc in documents]

    async def _arun(
        self,
        keywords: str,
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
    ) -> str | list[dict]:
        return self._run(keywords, None)


def get_retriever_tool(resources: List[Resource]) -> RetrieverTool | None:
    if not resources:
        return None
    logger.info(f"create retriever tool: {SELECTED_RAG_PROVIDER}")
    retriever = build_retriever()

    if not retriever:
        return None
    return RetrieverTool(retriever=retriever, resources=resources)
