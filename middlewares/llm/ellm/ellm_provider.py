"""Backward-compat shim. The implementation has moved to
:mod:`src.llms.providers.ellm`.

This module is kept only for any legacy import path; new code should import
``EllmChatModel`` directly from ``src.llms.providers.ellm``.
"""

from src.llms.providers.ellm import EllmChatModel  # noqa: F401

__all__ = ["EllmChatModel"]
