// SPDX-License-Identifier: MIT

/**
 * guwpToken 认证管理
 *
 * 从 URL 参数获取 guwpToken，写入 Cookie，后续请求自动携带。
 * 提供 getGuwpToken / clearGuwpToken 工具函数。
 */

const COOKIE_NAME = "guwpToken";
const COOKIE_MAX_AGE = 86400 * 7; // 7 天

/**
 * 从 URL 参数解析 guwpToken 并写入 Cookie
 * 应在页面加载时调用一次
 */
export function initGuwpToken(): string | null {
  if (typeof window === "undefined") return null;

  const params = new URLSearchParams(window.location.search);
  const tokenFromUrl = params.get("guwpToken");

  if (tokenFromUrl) {
    setGuwpTokenCookie(tokenFromUrl);
    // 清理 URL 中的 token 参数（不刷新页面）
    const url = new URL(window.location.href);
    url.searchParams.delete("guwpToken");
    window.history.replaceState({}, "", url.toString());
    return tokenFromUrl;
  }

  // 尝试从 Cookie 读取已有 token
  return getGuwpToken();
}

/**
 * 获取当前 guwpToken（从 Cookie 读取）
 */
export function getGuwpToken(): string | null {
  if (typeof document === "undefined") return null;

  const cookies = document.cookie.split(";");
  for (const cookie of cookies) {
    const [name, value] = cookie.trim().split("=");
    if (name === COOKIE_NAME && value) {
      return decodeURIComponent(value);
    }
  }
  return null;
}

/**
 * 写入 guwpToken 到 Cookie
 */
export function setGuwpTokenCookie(token: string): void {
  if (typeof document === "undefined") return;

  document.cookie = [
    `${COOKIE_NAME}=${encodeURIComponent(token)}`,
    `path=/`,
    `max-age=${COOKIE_MAX_AGE}`,
    `SameSite=Lax`,
  ].join("; ");
}

/**
 * 清除 guwpToken Cookie
 */
export function clearGuwpToken(): void {
  if (typeof document === "undefined") return;

  document.cookie = `${COOKIE_NAME}=; path=/; max-age=0; SameSite=Lax`;
}
