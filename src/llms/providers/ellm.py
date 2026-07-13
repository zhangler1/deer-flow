"""ELLM ChatOpenAI Provider with dynamic API key refresh.

This module provides ``EllmChatModel``, a custom ``ChatOpenAI`` subclass
designed for the BOCOM ELLM (Enterprise Large Language Model) gateway.

The ELLM gateway requires an ``api-key`` header (not the standard
``Authorization: Bearer`` header) and the key expires approximately every
25 minutes.  This provider:

1.  On initialisation, obtains an API key via the ELLM key-service endpoint
    and starts a background refresh thread.
2.  Before every LLM call, injects the latest valid key into
    ``default_headers["api-key"]`` so the request always carries a fresh key.

Configuration example (``conf.internal.yaml``)::

    BASIC_MODEL:
      platform: ellm
      model: Qwen3-235B-A22B
      base_url: http://eaip-chn-slb-7006.bocomm.com/ELLM.ELLM-ADAPTER.V-1.0/v1
      api_key_url: http://eaip-ellm-1.bocomm.com/ELLM.ELLM-OMSERVICE.V-1.0/createSceneApiKey.do
      scene_code: P2024146
      api_key_refresh_interval: 1800
      api_key_refresh_ahead: 300
      max_tokens: 4096
      temperature: 0.7
"""

from __future__ import annotations

import logging
from typing import Any, Iterator, AsyncIterator

from pydantic import Field, SecretStr
from langchain_core.language_models import LanguageModelInput
from langchain_core.messages import AIMessageChunk, BaseMessage
from langchain_core.outputs import ChatGenerationChunk, ChatResult
from langchain_openai import ChatOpenAI

from src.llms.providers.ellm_apikey_manager import EllmApiKeyManager

logger = logging.getLogger(__name__)

# Placeholder API key value to satisfy ChatOpenAI's api_key validation.
# The actual authentication is done via the "api-key" custom header.
_ELLM_PLACEHOLDER_API_KEY = "ellm-dynamic-key"


class EllmChatModel(ChatOpenAI):
    """ChatOpenAI with dynamic API key refresh for the BOCOM ELLM gateway.

    The ELLM gateway authenticates via an ``api-key`` header whose value
    expires approximately every 25 minutes.  This provider transparently
    refreshes the key in the background so that every LLM request carries
    a valid key without requiring a process restart.

    Custom configuration fields:

    - ``api_key_url``: URL of the ELLM key-service endpoint
      (e.g. ``http://eaip-ellm-1.bocomm.com/ELLM.ELLM-OMSERVICE.V-1.0/createSceneApiKey.do``)
    - ``scene_code``: Scene code for the ELLM key-service
      (e.g. ``P2024146``)
    - ``api_key_refresh_interval``: How often (in seconds) to refresh the key.
      Defaults to 1800 (30 minutes).
    - ``api_key_refresh_ahead``: How many seconds before expiry to trigger a
      refresh. Defaults to 300 (5 minutes).
    """

    # Custom configuration fields
    api_key_url: str = ""
    scene_code: str = ""
    api_key_refresh_interval: int = 1800
    api_key_refresh_ahead: int = 300
    force_refresh_min_interval: int = 600  # 失败后强制刷新最小间隔（秒）

    # 是否在流式输出时主动注入 💭 标签（由 _create_llm_use_conf 根据配置设置）
    inject_think_tag: bool = False

    # 必须在父类初始化校验前就存在一个占位 api_key
    openai_api_key: SecretStr = Field(
        default_factory=lambda: SecretStr(_ELLM_PLACEHOLDER_API_KEY),
        alias='api_key',
    )

    def model_post_init(self, __context: Any) -> None:
        """Initialise the API key manager and set up default headers.

        When ``api_key_url`` is empty, skip the ELLM key manager entirely
        and fall back to the static ``api_key`` configured in the YAML.
        This allows testing the EllmChatModel path (e.g. inject_think_tag)
        against non-ELLM endpoints such as DeepSeek.
        """
        if not self.api_key_url or not self.scene_code:
            logger.warning(
                "EllmChatModel: api_key_url or scene_code not configured — "
                "skipping ELLM key manager, using static api_key "
                "(model=%s)",
                self.model_name,
            )
            # Mark that we don't have a key manager so retry logic can skip.
            self._key_manager = None  # type: ignore[assignment]
            super().model_post_init(__context)
            return

        # Get or create the singleton key manager for this scene_code
        self._key_manager = EllmApiKeyManager.get_instance(
            api_key_url=self.api_key_url,
            scene_code=self.scene_code,
            refresh_interval=self.api_key_refresh_interval,
            refresh_ahead=self.api_key_refresh_ahead,
            force_refresh_min_interval=self.force_refresh_min_interval,
        )

        # Start the manager (initial key fetch + background refresh thread)
        self._key_manager.start()

        # Obtain initial key
        current_key = self._key_manager.get_api_key()

        # Inject the real key as a custom header.
        # The ELLM gateway expects "api-key" header, not "Authorization: Bearer".
        # Mutate in-place so the dict reference is shared with the underlying
        # OpenAI HTTP client (root_client._custom_headers).  If we create a new
        # dict here, _inject_latest_api_key() would later write to a different
        # object and the HTTP client would never see the refreshed key.
        if self.default_headers is None:
            self.default_headers = {}
        self.default_headers["api-key"] = current_key

        logger.info(
            "EllmChatModel initialised (scene_code=%s, model=%s)",
            self.scene_code,
            self.model_name,
        )

        super().model_post_init(__context)

    def _inject_latest_api_key(self) -> None:
        """Update default_headers with the latest API key from the manager.

        Mutates the dict **in-place** so that the underlying OpenAI HTTP
        clients (``root_client._custom_headers`` / ``root_async_client._custom_headers``)
        see the refreshed key.  Reassigning ``self.default_headers`` would
        create a new dict and break the reference — the HTTP clients would
        keep using the old (possibly expired) key forever.
        """
        # No key manager → using static api_key, nothing to inject.
        if self._key_manager is None:
            return
        try:
            current_key = self._key_manager.get_api_key()

            # 1) Mutate the Pydantic model's default_headers in-place.
            #    This dict is the same object referenced by the OpenAI HTTP
            #    client's _custom_headers (set during model_post_init before
            #    super().model_post_init() created the client).
            if self.default_headers is None:
                self.default_headers = {}
            self.default_headers["api-key"] = current_key

            # 2) Safety net: also sync the underlying OpenAI HTTP clients
            #    directly.  If a previous code path ever reassigned
            #    self.default_headers (breaking the shared reference), this
            #    ensures the clients still pick up the new key.
            for client in (self.root_client, self.root_async_client):
                if client is not None:
                    client._custom_headers["api-key"] = current_key
            # Observability: surface key age / remaining TTL / refresh-thread health.
            # At DEBUG for normal calls; escalate to WARNING when the key is
            # about to expire or the background refresh thread has died —
            # these are exactly the signals needed to diagnose the
            # "apikey 已过期" family of problems.
            try:
                status = self._key_manager.describe_status()
                expires_in = status.get("expires_in_sec", -1)
                thread_alive = status.get("thread_alive", False)
                if not thread_alive:
                    logger.warning(
                        "EllmChatModel: refresh thread DEAD at injection time "
                        "(scene_code=%s, model=%s, key_age=%.0fs, expires_in=%.0fs)",
                        self.scene_code,
                        self.model_name,
                        status.get("key_age_sec", -1),
                        expires_in,
                    )
                elif 0 < expires_in < 120:
                    logger.warning(
                        "EllmChatModel: api-key near expiry "
                        "(scene_code=%s, model=%s, expires_in=%.0fs)",
                        self.scene_code,
                        self.model_name,
                        expires_in,
                    )
                else:
                    logger.debug(
                        "EllmChatModel: api-key injected "
                        "(scene_code=%s, model=%s, key_age=%.0fs, expires_in=%.0fs, thread_alive=%s)",
                        self.scene_code,
                        self.model_name,
                        status.get("key_age_sec", -1),
                        expires_in,
                        thread_alive,
                    )
            except Exception:
                # Observability must never break the request path.
                pass
        except Exception as e:
            logger.warning(
                "EllmChatModel: failed to refresh api-key header, "
                "existing header will be used (error=%s)",
                e,
            )

    def _get_request_payload(
        self,
        input_: LanguageModelInput,
        *,
        stop: list[str] | None = None,
        **kwargs: Any,
    ) -> dict:
        """Inject the latest API key and strip user-message names for MiniMax."""
        # Refresh the key in default_headers before building the payload
        self._inject_latest_api_key()

        # Build the payload via the parent class
        payload = super()._get_request_payload(input_, stop=stop, **kwargs)

        # ---- MiniMax API 兼容 ----
        # MiniMax 要求同一请求中所有 role="user" 消息的 name 字段一致，
        # 否则返回 400 "user name must be consistent (2013)"。
        # LangGraph 工作流会给 HumanMessage 设置不同的 name（如
        # "researcher"、"feedback"、"coordinator"），导致 MiniMax 拒绝请求。
        # 移除 user 消息的 name 字段是安全的：其他 OpenAI 兼容提供商
        # （DeepSeek、OpenAI）均忽略此字段。
        messages = payload.get("messages", [])
        for msg in messages:
            if isinstance(msg, dict) and msg.get("role") == "user" and "name" in msg:
                del msg["name"]

        return payload

    # ------------------------------------------------------------------
    # 鉴权失败自动重试
    # ------------------------------------------------------------------

    @staticmethod
    def _is_auth_error(exc: BaseException) -> bool:
        """Detect authentication/permission errors from the ELLM gateway."""
        # openai SDK typed errors
        name = type(exc).__name__
        if name in ("AuthenticationError", "PermissionDeniedError"):
            return True
        # Fall back to HTTP status code
        status = getattr(exc, "status_code", None) or getattr(
            getattr(exc, "response", None), "status_code", None
        )
        return status in (401, 403)

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        """Override to retry once on auth failure after forced key refresh."""
        try:
            return super()._generate(messages, stop=stop, run_manager=run_manager, **kwargs)
        except Exception as e:
            if self._is_auth_error(e) and self._key_manager and self._key_manager.force_refresh_on_failure():
                logger.info(
                    "EllmChatModel: retrying _generate after forced key refresh "
                    "(scene_code=%s)",
                    self.scene_code,
                )
                self._inject_latest_api_key()
                return super()._generate(messages, stop=stop, run_manager=run_manager, **kwargs)
            raise

    async def _agenerate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        """Override to retry once on auth failure after forced key refresh."""
        try:
            return await super()._agenerate(messages, stop=stop, run_manager=run_manager, **kwargs)
        except Exception as e:
            if self._is_auth_error(e) and self._key_manager and self._key_manager.force_refresh_on_failure():
                logger.info(
                    "EllmChatModel: retrying _agenerate after forced key refresh "
                    "(scene_code=%s)",
                    self.scene_code,
                )
                self._inject_latest_api_key()
                return await super()._agenerate(messages, stop=stop, run_manager=run_manager, **kwargs)
            raise

    def _stream(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> Iterator[ChatGenerationChunk]:
        """Override to retry once on auth failure after forced key refresh."""
        try:
            yield from super()._stream(messages, stop=stop, run_manager=run_manager, **kwargs)
        except Exception as e:
            if self._is_auth_error(e) and self._key_manager and self._key_manager.force_refresh_on_failure():
                logger.info(
                    "EllmChatModel: retrying _stream after forced key refresh "
                    "(scene_code=%s)",
                    self.scene_code,
                )
                self._inject_latest_api_key()
                yield from super()._stream(messages, stop=stop, run_manager=run_manager, **kwargs)
            else:
                raise

    async def _astream(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> AsyncIterator[ChatGenerationChunk]:
        """Override to retry once on auth failure after forced key refresh.

        When ``inject_think_tag`` is True, prepend ``<think>\n`` to the
        first non-empty AI content chunk so the frontend can render the
        reasoning in a collapsible "thinking" section.
        """
        _injected = False
        try:
            async for chunk in super()._astream(messages, stop=stop, run_manager=run_manager, **kwargs):
                if self.inject_think_tag and not _injected:
                    msg = chunk.message
                    if isinstance(msg, AIMessageChunk) \
                       and isinstance(msg.content, str) and msg.content:
                        msg.content = "<think>\n" + msg.content
                        _injected = True
                yield chunk
        except Exception as e:
            if self._is_auth_error(e) and self._key_manager and self._key_manager.force_refresh_on_failure():
                logger.info(
                    "EllmChatModel: retrying _astream after forced key refresh "
                    "(scene_code=%s)",
                    self.scene_code,
                )
                self._inject_latest_api_key()
                async for chunk in super()._astream(messages, stop=stop, run_manager=run_manager, **kwargs):
                    if self.inject_think_tag and not _injected:
                        msg = chunk.message
                        if isinstance(msg, AIMessageChunk) \
                           and isinstance(msg.content, str) and msg.content:
                            msg.content = "<think>\n" + msg.content
                            _injected = True
                    yield chunk
            else:
                raise
