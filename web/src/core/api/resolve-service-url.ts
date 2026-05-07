// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

import { env } from "~/env";

/**
 * 解析后端服务 URL。
 *
 * 策略：
 * 1. 若显式设置了 NEXT_PUBLIC_API_URL（本地直连后端场景），则拼接该绝对 URL。
 * 2. 否则走同域相对路径：<basePath>/api/<path>，由 nginx 代理到后端。
 *    这样子路径部署（外层网关转 /deep-research-deerflow/*）的情况下
 *    浏览器会请求 /deep-research-deerflow/api/xxx，命中正确的 location。
 */
export function resolveServiceURL(path: string) {
  const clean = path.replace(/^\.?\/+/, "");
  if (env.NEXT_PUBLIC_API_URL) {
    let baseUrl = env.NEXT_PUBLIC_API_URL;
    if (!baseUrl.endsWith("/")) {
      baseUrl += "/";
    }
    return new URL(clean, baseUrl).toString();
  }
  const basePath = env.NEXT_PUBLIC_BASE_PATH ?? "";
  return `${basePath}/api/${clean}`;
}
