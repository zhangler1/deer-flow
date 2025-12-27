// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

import { cn } from "~/lib/utils";

// 默认的 favicon 图标（使用本地静态资源，内网环境友好）
const DEFAULT_FAVICON = "/images/favicon-standard.png";

export function FavIcon({
  className,
  url,
  title,
}: {
  className?: string;
  url: string;
  title?: string;
}) {
  // 检查 URL 是否有效
  const getFaviconUrl = (urlString: string): string => {
    // 如果 URL 为空或无效，返回默认图标
    if (!urlString || urlString.trim() === "") {
      return DEFAULT_FAVICON;
    }
    
    try {
      const urlObj = new URL(urlString);
      return urlObj.origin + "/favicon.ico";
    } catch (error) {
      // URL 无效，返回默认图标
      return DEFAULT_FAVICON;
    }
  };
  
  return (
    <img
      className={cn("bg-accent h-4 w-4 rounded-full shadow-sm", className)}
      width={16}
      height={16}
      src={getFaviconUrl(url)}
      alt={title}
      onError={(e) => {
        // 加载失败时使用默认图标（内网环境友好）
        // 避免循环加载：如果已经是默认图标了就不再重试
        if (e.currentTarget.src.indexOf(DEFAULT_FAVICON) === -1) {
          e.currentTarget.src = DEFAULT_FAVICON;
        }
      }}
    />
  );
}
