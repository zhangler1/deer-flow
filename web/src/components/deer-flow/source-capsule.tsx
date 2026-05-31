"use client";

import { useCallback, useState, useRef } from "react";
import { ExternalLink } from "lucide-react";

import { cn } from "~/lib/utils";
import { FavIcon } from "./fav-icon";

// ── 类型 ──────────────────────────────────────────

export interface SourceCapsuleProps {
  /** 来源 URL */
  url: string;
  /** 域名 */
  domain: string;
  /** 标题 */
  title?: string;
  /** 摘要（可选） */
  snippet?: string;
}

// ── 组件 ──────────────────────────────────────────

/**
 * 来源胶囊组件（用于研究过程中）
 * 
 * 默认显示为小胶囊（域名 + favicon），hover 时弹出详细信息卡片
 */
export function SourceCapsule({ url, domain, title, snippet }: SourceCapsuleProps) {
  const [showCard, setShowCard] = useState(false);
  const hoverTimeout = useRef<ReturnType<typeof setTimeout> | null>(null);
  const leaveTimeout = useRef<ReturnType<typeof setTimeout> | null>(null);

  const displayTitle = title || "未命名文档";
  const displayDomain = domain || extractDomain(url);

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

      // 正常点击 → 在新标签页打开
      window.open(url, "_blank", "noopener,noreferrer");
    },
    [url],
  );

  return (
    <span className="relative inline-block">
      {/* 小胶囊（默认显示） */}
      <span
        className={cn(
          "inline-flex cursor-pointer select-none items-center gap-1.5",
          "rounded-full border border-border/50 bg-muted/30",
          "px-2 py-0.5 text-xs text-muted-foreground",
          "hover:bg-muted hover:text-foreground",
          "transition-all duration-150",
        )}
        onClick={handleClick}
        onMouseEnter={handleMouseEnter}
        onMouseLeave={handleMouseLeave}
        role="button"
        tabIndex={0}
        aria-label={`查看来源: ${displayTitle}`}
      >
        <FavIcon url={url} className="h-3.5 w-3.5 shrink-0" title={displayTitle} />
        <span className="truncate max-w-[80px]">{displayDomain}</span>
      </span>

      {/* 弹出卡片（hover 时显示） */}
      {showCard && (
        <span
          className={cn(
            "absolute z-50 left-1/2 -translate-x-1/2 bottom-full mb-2",
            "w-[280px] rounded-xl border border-border/60 bg-popover px-3 py-2.5 shadow-md",
            "animate-in fade-in-0 zoom-in-95 duration-150",
            "cursor-pointer",
          )}
          onMouseEnter={handleCardMouseEnter}
          onMouseLeave={handleCardMouseLeave}
          onClick={handleClick}
        >
          {/* 第一排：favicon + 域名 + 外部链接图标 */}
          <span className="flex items-center justify-between gap-1.5 mb-1.5">
            <span className="flex items-center gap-1.5">
              <FavIcon url={url} className="h-3.5 w-3.5 shrink-0 rounded-sm" title={displayTitle} />
              <span className="text-xs text-muted-foreground truncate leading-none">
                {displayDomain}
              </span>
            </span>
            <ExternalLink className="h-3 w-3 text-muted-foreground shrink-0" />
          </span>
          
          {/* 第二行：标题 */}
          <span className="block text-[13px] font-semibold leading-tight text-foreground line-clamp-2 mb-1.5">
            {displayTitle}
          </span>
          
          {/* 第三行：摘要（如果有） */}
          {snippet && (
            <span className="block text-xs text-muted-foreground line-clamp-3 leading-relaxed">
              {snippet}
            </span>
          )}
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
