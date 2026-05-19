"""Backward-compat shim. The implementation has moved to
:mod:`src.llms.providers.ellm_apikey_manager`.

This module is kept only for any legacy import path; new code should import
``EllmApiKeyManager`` directly from ``src.llms.providers.ellm_apikey_manager``.
"""

from src.llms.providers.ellm_apikey_manager import (  # noqa: F401
    EllmApiKeyManager,
    DEFAULT_REFRESH_INTERVAL,
    DEFAULT_REFRESH_AHEAD,
    DEFAULT_REQUEST_TIMEOUT,
)

__all__ = [
    "EllmApiKeyManager",
    "DEFAULT_REFRESH_INTERVAL",
    "DEFAULT_REFRESH_AHEAD",
    "DEFAULT_REQUEST_TIMEOUT",
]
