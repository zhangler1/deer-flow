// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

"use client";

import Image from "next/image";
import { useTheme } from "next-themes";
import { useEffect, useState } from "react";

export function Logo() {
  const { theme } = useTheme();
  const [mounted, setMounted] = useState(false);
  
  const handleClick = (e: React.MouseEvent<HTMLAnchorElement>) => {
    e.preventDefault();
    // 强制刷新并重新加载问答页面
    window.location.href = '/chat';
  };

  // 等待组件挂载后再渲染主题相关内容，避免hydration错误
  useEffect(() => {
    setMounted(true);
  }, []);

  // 判断是否为交心主题
  const isJiaoxinTheme = mounted && theme === "jiaoxin";

  return (
    <a
      className="flex items-center gap-2 opacity-70 transition-opacity duration-300 hover:opacity-100 cursor-pointer"
      href="/chat"
      onClick={handleClick}
    >
      {/* 在mounted之前，先渲染一个占位符，避免布局偏移 */}
      {!mounted ? (
        <span className="text-2xl">💡</span>
      ) : isJiaoxinTheme ? (
        // 交心主题：显示AI机器人图标
        <Image
          src="/images/jiaoxin-logo.png"
          alt="交心深度研究"
          width={32}
          height={32}
          className="object-contain"
        />
      ) : (
        // 其他主题：显示原来的灯泡emoji
        <span className="text-2xl">💡</span>
      )}
      <span>交心深度研究</span>
    </a>
  );
}
