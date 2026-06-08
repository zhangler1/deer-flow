"use client";

// SPDX-License-Identifier: MIT

/**
 * GuwpToken 初始化组件
 *
 * 在页面加载时从 URL 参数解析 guwpToken 并写入 Cookie。
 * 放在根 layout 中确保任何页面都能正确初始化 token。
 */

import { useEffect } from "react";
import { initGuwpToken } from "~/core/utils/auth-token";

export function GuwpTokenInitializer() {
  useEffect(() => {
    initGuwpToken();
  }, []);

  return null;
}
