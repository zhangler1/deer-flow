// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

import { env } from "~/env";

/**
 * 获取当前构建配置的 basePath（NEXT_PUBLIC_BASE_PATH），用于需要手动拼接
 * 子路径前缀的场景（如 window.location.href、public 目录下的静态资源、fetch 绝对路径等）。
 *
 * Next.js 的 <Link>、useRouter、redirect、next/image 的 _next/image 会自动处理 basePath，
 * 这个工具只用于 Next 不会自动处理的地方。
 */
export function getBasePath(): string {
  return env.NEXT_PUBLIC_BASE_PATH ?? "";
}

/**
 * 把以 "/" 开头的绝对路径拼上 basePath。
 * 例：basePath=/deep-research-deerflow, withBasePath("/images/x.png")
 *   → "/deep-research-deerflow/images/x.png"
 * 若 basePath 为空则原样返回。
 */
export function withBasePath(path: string): string {
  const bp = getBasePath();
  if (!bp) return path;
  if (!path.startsWith("/")) return `${bp}/${path}`;
  return `${bp}${path}`;
}
