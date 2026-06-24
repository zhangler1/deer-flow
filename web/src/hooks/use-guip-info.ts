// SPDX-License-Identifier: MIT

"use client";

/**
 * useGuipInfo - GUIP 框架集成 Hook
 *
 * 等待 GuipAPI.xc2.js 注入的 `window.promise.globalInfo()` 就绪后，
 * 暴露用户信息、全局配置、模块大参数及 openModule 操作。
 *
 * 用法：
 * ```tsx
 * const { userInfo, globalInfo, moduleParam, guwpToken, openModule, isReady } = useGuipInfo();
 * ```
 */

import { useCallback, useEffect, useState } from "react";

/** hook 返回值 */
export interface UseGuipInfoReturn {
  /** globalInfo 是否已就绪 */
  isReady: boolean;
  /** 加载错误（如有） */
  error: Error | null;
  /** 当前登录用户信息 */
  userInfo: GuipUserInfo | null;
  /** 完整 globalInfo 对象 */
  globalInfo: GuipGlobalInfo | null;
  /**
   * 模块大参数（从 guipModule.param 获取）。
   * 当 param 为 null 时表示大参数未通过 URL 传递，需另行获取。
   */
  moduleParam: string | null | undefined;
  /** 当前模块 ID */
  moduleId: string | undefined;
  /** 当前功能码 */
  funcCode: string | undefined;
  /** guwpToken（优先从 GuipAPI 获取，降级从 Cookie 获取） */
  guwpToken: string | null;
  /** guipToken（会话令牌） */
  guipToken: string | null;
  /** 打开子模块 */
  openModule: (options: OpenModule2Options) => string | undefined;
  /** 关闭模块（不传参则关闭当前模块/页面） */
  closeModule: (moduleId?: string) => void;
}

/**
 * 检查 GuipAPI 是否已加载到 window
 */
function isGuipApiLoaded(): boolean {
  return typeof window !== "undefined" && typeof window.promise?.globalInfo === "function";
}

/**
 * 从 Cookie 读取 guwpToken（降级方案，与 auth-token.ts 逻辑一致）
 */
function getGuwpTokenFromCookie(): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie
    .split(";")
    .map((c) => c.trim())
    .find((c) => c.startsWith("guwpToken="));
  return match ? decodeURIComponent(match.split("=")[1] ?? "") : null;
}

export function useGuipInfo(): UseGuipInfoReturn {
  const [isReady, setIsReady] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [userInfo, setUserInfo] = useState<GuipUserInfo | null>(null);
  const [globalInfoState, setGlobalInfoState] = useState<GuipGlobalInfo | null>(null);
  const [moduleParam, setModuleParam] = useState<string | null | undefined>(undefined);
  const [moduleId, setModuleId] = useState<string | undefined>(undefined);
  const [funcCode, setFuncCode] = useState<string | undefined>(undefined);
  const [guwpToken, setGuwpToken] = useState<string | null>(null);
  const [guipToken, setGuipToken] = useState<string | null>(null);

  useEffect(() => {
    if (typeof window === "undefined") return;

    // 轮询等待 GuipAPI 脚本加载完成（最多 5 秒）
    const MAX_WAIT_MS = 5000;
    const POLL_INTERVAL_MS = 100;
    let elapsed = 0;

    const poll = setInterval(() => {
      elapsed += POLL_INTERVAL_MS;

      if (isGuipApiLoaded()) {
        clearInterval(poll);
        initFromGuipApi();
        return;
      }

      if (elapsed >= MAX_WAIT_MS) {
        clearInterval(poll);
        setError(new Error("GuipAPI.xc2.js 加载超时（5s），请检查脚本是否正确引入"));
        // 降级：尝试从 Cookie 获取 guwpToken
        setGuwpToken(getGuwpTokenFromCookie());
      }
    }, POLL_INTERVAL_MS);

    return () => clearInterval(poll);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  /** 从 GuipAPI 读取所有信息 */
  function initFromGuipApi() {
    try {
      // 获取 token
      const wpToken = window.getGuwpToken?.() || getGuwpTokenFromCookie();
      setGuwpToken(wpToken || null);

      const gToken = window.getGuipToken?.();
      setGuipToken(gToken || null);

      // 读取 guipModule（URL 解析结果）
      const gm = window.guipModule;
      setModuleId(gm?.moduleId);
      setFuncCode(gm?.funcCode);
      setModuleParam(gm?.param ?? undefined);

      // 等待 globalInfo 就绪（最多延迟 3s，由 GuipAPI 内部处理）
      window.promise
        .globalInfo()
        .then((info) => {
          setGlobalInfoState(info);
          setUserInfo(info.userInfo ?? null);
          setIsReady(true);
        })
        .catch((err: unknown) => {
          setError(err instanceof Error ? err : new Error(String(err)));
          setIsReady(true); // 即使出错也标记 ready，允许业务降级处理
        });
    } catch (err) {
      setError(err instanceof Error ? err : new Error(String(err)));
      setIsReady(true);
    }
  }

  const openModule = useCallback((options: OpenModule2Options) => {
    if (!isGuipApiLoaded()) {
      console.warn("[useGuipInfo] GuipAPI 未加载，openModule 不可用");
      return undefined;
    }
    return window.openModule2(options);
  }, []);

  const closeModule = useCallback((mid?: string) => {
    if (!isGuipApiLoaded()) {
      console.warn("[useGuipInfo] GuipAPI 未加载，closeModule 不可用");
      return;
    }
    window.closeModule(mid);
  }, []);

  return {
    isReady,
    error,
    userInfo,
    globalInfo: globalInfoState,
    moduleParam,
    moduleId,
    funcCode,
    guwpToken,
    guipToken,
    openModule,
    closeModule,
  };
}
