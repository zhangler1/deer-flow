# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

from typing import List, Dict, Any
from pydantic import BaseModel, Field

from src.server.rag_request import RAGConfigResponse


class ReporterOption(BaseModel):
    """A single reporter model option."""
    key: str = Field(..., description="The option key name in REPORTER_MODEL_OPTIONS")
    model: str = Field(..., description="The model name")


class ReporterOptions(BaseModel):
    """Reporter model options returned by /api/config."""
    default: str = Field("", description="The default option key")
    options: list[ReporterOption] = Field(default_factory=list, description="Available reporter model options")


class ConfigResponse(BaseModel):
    """Response model for server config."""

    rag: RAGConfigResponse = Field(..., description="The config of the RAG")
    models: dict[str, list[str]] = Field(..., description="The configured models")
    reporter_options: ReporterOptions = Field(..., description="Reporter model selection options")
