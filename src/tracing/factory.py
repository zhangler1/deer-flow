# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""Langfuse tracing callback factory.

Creates a Langfuse LangChain CallbackHandler when Langfuse tracing
is enabled and properly configured. Uses lazy imports so that the
langfuse package is only loaded when actually needed.
"""

from __future__ import annotations

from typing import Any

from src.config.tracing_config import (
    get_langfuse_config,
    is_langfuse_configured,
    validate_langfuse_config,
)


def _create_langfuse_handler(config) -> Any:
    """Create a Langfuse CallbackHandler for LangChain.

    langfuse>=4 initializes project-specific credentials through the
    client singleton; the LangChain callback then attaches to that
    configured client. This two-step initialization is required.

    Args:
        config: A LangfuseConfig instance.

    Returns:
        A Langfuse CallbackHandler instance.
    """
    from langfuse import Langfuse
    from langfuse.langchain import CallbackHandler as LangfuseCallbackHandler

    # Step 1: Initialize the Langfuse client singleton with credentials.
    # This must happen before creating the CallbackHandler so that the
    # handler can discover the configured client.
    Langfuse(
        secret_key=config.secret_key,
        public_key=config.public_key,
        host=config.host,
    )

    # Step 2: Create the LangChain callback handler. It attaches to
    # the client singleton initialized above via the public_key.
    return LangfuseCallbackHandler(public_key=config.public_key)


def build_langfuse_callback() -> Any | None:
    """Build a Langfuse callback for LangChain if configured.

    Returns:
        A LangfuseCallbackHandler if Langfuse is enabled and fully
        configured, or None if Langfuse is not enabled.

    Raises:
        ValueError: If Langfuse is explicitly enabled but required
            credentials are missing.
        RuntimeError: If the Langfuse handler fails to initialize.
    """
    if not is_langfuse_configured():
        # Not enabled or missing credentials — validate to produce
        # an explicit error if the user enabled it but misconfigured.
        validate_langfuse_config()
        return None

    config = get_langfuse_config()

    try:
        return _create_langfuse_handler(config)
    except Exception as exc:
        raise RuntimeError(
            f"Langfuse tracing initialization failed: {exc}"
        ) from exc
