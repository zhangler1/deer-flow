"use client";

// SPDX-License-Identifier: MIT

/**
 * GuwpToken 初始化组件
 *
 * 在页面加载时初始化 guwpToken：
 * 1. 若 GuipAPI.xc2.js 已加载，优先使用其 getGuwpToken()（从 URL/moduleData/globalInfo 三级来源获取）
 * 2. 否则降级为直接从 URL 参数解析
 * 获取到 token 后写入 Cookie，后续请求自动携带。
 * 放在根 layout 中确保任何页面都能正确初始化 token。
 */

import { useEffect } from "react";
import { initGuwpToken, setGuwpTokenCookie } from "~/core/utils/auth-token";

export function GuwpTokenInitializer() {
  useEffect(() => {
    // GuipAPI.xc2.js 由 beforeInteractive Script 注入，此时应已就绪
    const guipGetToken = typeof window !== "undefined" ? window.getGuwpToken : undefined;
    const tokenFromGuip = guipGetToken?.();

    if (tokenFromGuip) {
      // GuipAPI 已提供 token，直接写 Cookie（避免重复解析 URL）
      setGuwpTokenCookie(tokenFromGuip);
    } else {
      // 降级：走原有逻辑，从 URL 参数解析
      initGuwpToken();
    }
  }, []);

  return null;
}
