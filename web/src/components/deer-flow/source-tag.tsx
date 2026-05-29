"use client";

import { useCallback } from "react";

import { useSourceStore, type SourceDetail } from "~/core/source-store";
import { cn } from "~/lib/utils";

import { Tooltip } from "./tooltip";

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
 * 渲染为行内可点击的上标标签 [N]，点击后：
 * 1. 优先通过 URL 在 sourceStore 中查找匹配 → 打开详情抽屉
 * 2. 若未找到（兜底）→ 直接在新标签页打开 URL
 *
 * Ctrl+Click / Cmd+Click → 始终直接在新标签页打开原始 URL
 */
export function SourceTag({ index, url, references }: SourceTagProps) {
  const openSourceByUrl = useSourceStore((s) => s.openSourceByUrl);
  const storeReferences = useSourceStore((s) => s.references);

  // 尝试从 props references 或 store references 中找到标题
  const allRefs = references ?? storeReferences;
  const matchedRef = allRefs.find((r) => r.url === url);
  const title = matchedRef?.title ?? extractDomain(url);

  const handleClick = useCallback(
    (e: React.MouseEvent) => {
      e.preventDefault();
      e.stopPropagation();

      // Ctrl+Click / Cmd+Click → 直接在新标签页打开
      if (e.ctrlKey || e.metaKey) {
        console.log('[SourceTag] Ctrl/Cmd+Click, 直接跳转:', url);
        window.open(url, "_blank", "noopener,noreferrer");
        return;
      }

      // 正常点击：尝试在 store 中匹配并打开抽屉
      const refs = useSourceStore.getState().references;
      const found = refs.some((r) => r.url === url);

      console.group('[SourceTag] 点击调试');
      console.log('点击的 URL:', url);
      console.log('store references 数量:', refs.length);
      console.log('store references URLs:', refs.map(r => r.url));
      console.log('严格匹配结果:', found);
      if (!found && refs.length > 0) {
        // 打印前3个 reference 的 URL 对比
        console.log('--- URL 对比（前5个）---');
        refs.slice(0, 5).forEach((r, i) => {
          console.log(`  [${i}] store: "${r.url}"`);
          console.log(`       click: "${url}"`);
          console.log(`       相等: ${r.url === url}`);
        });
      }
      console.groupEnd();

      if (found) {
        console.log('[SourceTag] ✅ 匹配成功，打开抽屉');
        openSourceByUrl(url);
      } else {
        console.log('[SourceTag] ❌ 匹配失败，跳转新标签页');
        window.open(url, "_blank", "noopener,noreferrer");
      }
    },
    [url, openSourceByUrl],
  );

  return (
    <Tooltip title={title}>
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
        role="button"
        tabIndex={0}
        aria-label={`来源 ${index}: ${title}`}
      >
        {index}
      </span>
    </Tooltip>
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
