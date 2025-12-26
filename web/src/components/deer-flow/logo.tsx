// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

"use client";

export function Logo() {
  const handleClick = (e: React.MouseEvent<HTMLAnchorElement>) => {
    e.preventDefault();
    // 强制刷新并重新加载问答页面
    window.location.href = '/chat';
  };

  return (
    <a
      className="opacity-70 transition-opacity duration-300 hover:opacity-100 cursor-pointer"
      href="/chat"
      onClick={handleClick}
    >
      💡 交心深度研究
    </a>
  );
}
