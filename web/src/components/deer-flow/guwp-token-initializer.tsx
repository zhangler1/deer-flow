"use client";

// SPDX-License-Identifier: MIT

/**
 * GuwpToken + UserInfo 初始化组件
 *
 * 在页面加载时初始化：
 * 1. guwpToken：若 GuipAPI.xc2.js 已加载，优先使用其 getGuwpToken()，否则降级从 URL 参数解析
 * 2. userInfo：等待 GuipAPI globalInfo() 就绪后，将完整用户信息存入 settings store，
 *    后续请求通过 X-User-Info 请求头直传给后端，避免每次都走 cookie → queryUserInfo 内网接口
 *
 * 放在根 layout 中确保任何页面都能正确初始化 token 和 userInfo。
 */

import { useEffect } from "react";
import { initGuwpToken, setGuwpTokenCookie } from "~/core/utils/auth-token";
import { setUserInfo } from "~/core/store/settings-store";

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

    // 从 GuipAPI globalInfo 获取完整用户信息并存入 settings store
    // 后端中间件优先从 X-User-Info 请求头解析，失败时才降级走 cookie → queryUserInfo 接口
    if (typeof window !== "undefined" && typeof window.promise?.globalInfo === "function") {
      window.promise
        .globalInfo()
        .then((info) => {
          if (info?.userInfo) {
            setUserInfo(info.userInfo);
          }
        })
        .catch((err: unknown) => {
          console.warn("[GuwpTokenInitializer] globalInfo 获取失败，后端将降级走 cookie 认证", err);
        });
    }
  }, []);

  return null;
}
