# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

from typing import List, Dict, Any
from pydantic import BaseModel, Field

from src.server.rag_request import RAGConfigResponse


class CustomSearchRepositoryConfig(BaseModel):
    """Custom search repository configuration model."""
    
    id: str = Field(..., description="Repository ID")
    name: str = Field(..., description="Repository display name")
    description: str = Field(..., description="Repository description")
    repository: str = Field(..., description="Repository internal name")


class ConfigResponse(BaseModel):
    """Response model for server config."""

    rag: RAGConfigResponse = Field(..., description="The config of the RAG")
    models: dict[str, list[str]] = Field(..., description="The configured models")
    custom_search_repositories: List[CustomSearchRepositoryConfig] = Field(
        default_factory=list, 
        description="Available custom search repositories"
    )
