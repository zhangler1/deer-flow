# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""Langfuse tracing configuration module.

Reads Langfuse settings from environment variables and provides
a thread-safe, lazily-initialized singleton configuration object.
"""

import os
import threading

from pydantic import BaseModel, Field

_config_lock = threading.Lock()


class LangfuseConfig(BaseModel):
    """Configuration for Langfuse tracing."""

    enabled: bool = Field(...)
    public_key: str | None = Field(...)
    secret_key: str | None = Field(...)
    host: str = Field(...)

    @property
    def is_configured(self) -> bool:
        """Return True if Langfuse is enabled and both keys are present."""
        return self.enabled and bool(self.public_key) and bool(self.secret_key)

    def validate(self) -> None:
        """Validate that required credentials are present when enabled.

        Raises:
            ValueError: If Langfuse is enabled but required settings are missing.
        """
        if not self.enabled:
            return
        missing: list[str] = []
        if not self.public_key:
            missing.append("LANGFUSE_PUBLIC_KEY")
        if not self.secret_key:
            missing.append("LANGFUSE_SECRET_KEY")
        if missing:
            raise ValueError(
                f"Langfuse tracing is enabled but required settings are missing: "
                f"{', '.join(missing)}"
            )


_TRUTHY_VALUES = {"1", "true", "yes", "on"}


def _env_flag(name: str) -> bool:
    """Return the boolean value of an environment variable."""
    value = os.environ.get(name)
    if value is not None and value.strip():
        return value.strip().lower() in _TRUTHY_VALUES
    return False


def _first_env_value(*names: str) -> str | None:
    """Return the first non-empty environment value from candidate names."""
    for name in names:
        value = os.environ.get(name)
        if value and value.strip():
            return value.strip()
    return None


_langfuse_config: LangfuseConfig | None = None


def get_langfuse_config() -> LangfuseConfig:
    """Get the current Langfuse configuration from environment variables.

    Uses double-checked locking for thread-safe lazy initialization.
    The result is cached; restart the process to pick up env changes.
    """
    global _langfuse_config
    if _langfuse_config is not None:
        return _langfuse_config
    with _config_lock:
        if _langfuse_config is not None:
            return _langfuse_config
        _langfuse_config = LangfuseConfig(
            enabled=_env_flag("LANGFUSE_TRACING"),
            public_key=_first_env_value("LANGFUSE_PUBLIC_KEY"),
            secret_key=_first_env_value("LANGFUSE_SECRET_KEY"),
            host=_first_env_value("LANGFUSE_BASE_URL") or "https://cloud.langfuse.com",
        )
        return _langfuse_config


def is_langfuse_configured() -> bool:
    """Check if Langfuse tracing is enabled and fully configured."""
    return get_langfuse_config().is_configured


def validate_langfuse_config() -> None:
    """Validate that Langfuse configuration is complete if enabled.

    Raises:
        ValueError: If Langfuse is enabled but required settings are missing.
    """
    get_langfuse_config().validate()
