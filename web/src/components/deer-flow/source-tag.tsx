"use client";

import { useCallback, useState, useRef } from "react";

import { useSourceStore, type SourceDetail } from "~/core/source-store";
import { cn } from "~/lib/utils";

import { FavIcon } from "./fav-icon";

// ── 类型 ──────────────────────────────────────────

export interface SourceTagProps {
  /** 来源序号（从1开始） */
  index: number;
  /** 来源 URL */
  url: string;
  /** 来源引用列表（可选，用于 tooltip 标题查找） */
  references?: SourceDetail[];
}

// ── 组件 ──────────────────────────────────────────

/**
 * 溯源标签组件
 *
 * 渲染为行内可点击的上标标签 [N]，悬停弹出溯源卡片，点击后：
 * 1. 优先通过 URL 在 sourceStore 中查找匹配 → 打开详情抽屉
 * 2. 若未找到（兜底）→ 直接在新标签页打开 URL
 *
 * Ctrl+Click / Cmd+Click → 始终直接在新标签页打开原始 URL
 */
export function SourceTag({ index, url, references }: SourceTagProps) {
  const openSourceByUrl = useSourceStore((s) => s.openSourceByUrl);
  const storeReferences = useSourceStore((s) => s.references);
  const [showCard, setShowCard] = useState(false);
  const hoverTimeout = useRef<ReturnType<typeof setTimeout> | null>(null);
  const leaveTimeout = useRef<ReturnType<typeof setTimeout> | null>(null);

  // 尝试从 props references 或 store references 中找到标题
  const allRefs = references ?? storeReferences;
  const matchedRef = allRefs.find((r) => r.url === url);
  const title = matchedRef?.title ?? extractDomain(url);
  const domain = matchedRef?.domain ?? extractDomain(url);

  const handleMouseEnter = useCallback(() => {
    if (leaveTimeout.current) {
      clearTimeout(leaveTimeout.current);
      leaveTimeout.current = null;
    }
    hoverTimeout.current = setTimeout(() => {
      setShowCard(true);
    }, 300);
  }, []);

  const handleMouseLeave = useCallback(() => {
    if (hoverTimeout.current) {
      clearTimeout(hoverTimeout.current);
      hoverTimeout.current = null;
    }
    leaveTimeout.current = setTimeout(() => {
      setShowCard(false);
    }, 200);
  }, []);

  const handleCardMouseEnter = useCallback(() => {
    if (leaveTimeout.current) {
      clearTimeout(leaveTimeout.current);
      leaveTimeout.current = null;
    }
  }, []);

  const handleCardMouseLeave = useCallback(() => {
    leaveTimeout.current = setTimeout(() => {
      setShowCard(false);
    }, 200);
  }, []);

  const handleClick = useCallback(
    (e: React.MouseEvent) => {
      e.preventDefault();
      e.stopPropagation();

      // Ctrl+Click / Cmd+Click → 直接在新标签页打开
      if (e.ctrlKey || e.metaKey) {
        window.open(url, "_blank", "noopener,noreferrer");
        return;
      }

      // 正常点击：尝试在 store 中匹配并打开抽屉
      const refs = useSourceStore.getState().references;
      const found = refs.some((r) => r.url === url);

      if (found) {
        openSourceByUrl(url);
      } else {
        window.open(url, "_blank", "noopener,noreferrer");
      }
    },
    [url, openSourceByUrl],
  );

  return (
    <span className="relative inline-block">
      <span
        className={cn(
          "inline-flex cursor-pointer select-none items-center justify-center",
          "min-w-[18px] h-[18px] px-[4px] rounded-full",
          "text-[11px] font-semibold leading-none",
          "bg-blue-500 text-white",
          "hover:bg-blue-600 hover:scale-110",
          "dark:bg-blue-400 dark:text-gray-900",
          "dark:hover:bg-blue-300",
          "transition-all duration-150",
          "align-super",
          "shadow-sm",
        )}
        onClick={handleClick}
        onMouseEnter={handleMouseEnter}
        onMouseLeave={handleMouseLeave}
        role="button"
        tabIndex={0}
        aria-label={`来源 ${index}: ${title}`}
      >
        {index}
      </span>

      {/* 溯源卡片 - 悬停弹出 */}
      {showCard && (
        <span
          className={cn(
            "absolute z-50 left-1/2 -translate-x-1/2 bottom-full mb-2",
            "w-[280px] rounded-lg border border-border bg-popover p-3 shadow-lg",
            "animate-in fade-in-0 zoom-in-95 duration-150",
            "cursor-pointer",
          )}
          onMouseEnter={handleCardMouseEnter}
          onMouseLeave={handleCardMouseLeave}
          onClick={handleClick}
        >
          {/* 卡片头部：来源图标 + 域名 */}
          <span className="flex items-center gap-2 mb-1.5">
            <FavIcon url={url} className="h-4 w-4 shrink-0" title={title} />
            <span className="text-xs text-muted-foreground truncate">
              {domain}
            </span>
          </span>
          {/* 卡片标题 */}
          <span className="block text-sm font-medium leading-snug text-foreground line-clamp-2">
            {title}
          </span>
        </span>
      )}
    </span>
  );
}

// ── 工具函数 ──────────────────────────────────────

/** 从 URL 提取域名 */
function extractDomain(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return url;
  }
}
