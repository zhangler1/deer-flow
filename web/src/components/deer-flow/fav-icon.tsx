// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

import { cn } from "~/lib/utils";

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
      return "https://perishablepress.com/wp/wp-content/images/2021/favicon-standard.png";
    }
    
    try {
      const urlObj = new URL(urlString);
      return urlObj.origin + "/favicon.ico";
    } catch (error) {
      // URL 无效，返回默认图标
      return "https://perishablepress.com/wp/wp-content/images/2021/favicon-standard.png";
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
        e.currentTarget.src =
          "https://perishablepress.com/wp/wp-content/images/2021/favicon-standard.png";
      }}
    />
  );
}
