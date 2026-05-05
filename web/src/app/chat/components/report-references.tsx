"use client";

import { ExternalLink, Globe, BookOpen } from "lucide-react";
import { useMemo } from "react";

import { FavIcon } from "~/components/deer-flow/fav-icon";
import { useStore } from "~/core/store";
import { parseJSON } from "~/core/utils";
import { cn } from "~/lib/utils";

// ── 类型 ──────────────────────────────────────────

/** 参考资料条目 */
export interface ReferenceItem {
  /** 唯一标识（URL 本身去重用） */
  url: string;
  /** 页面标题 */
  title: string;
  /** 域名 */
  domain: string;
}

// ── 数据提取 ──────────────────────────────────────

/** 从 URL 提取域名 */
function extractDomain(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return url;
  }
}

/** 搜索工具名列表 */
const SEARCH_TOOLS = new Set([
  "web_search",
  "domain_fin_search",
  "online_search",
  "industry_report_search",
  "product_search",
  "product_instance_search",
  "news_search",
  "news_detail_search",
]);

/** 爬虫工具名列表 */
const CRAWL_TOOLS = new Set(["crawl_tool", "batch_crawl_tool"]);

/** 从 researchId 对应的所有 activity 消息中提取参考资料 */
function extractReferences(
  researchId: string,
): ReferenceItem[] {
  const state = useStore.getState();
  const activityIds = state.researchActivityIds.get(researchId);
  if (!activityIds) return [];

  const seen = new Set<string>();
  const refs: ReferenceItem[] = [];

  for (const msgId of activityIds) {
    const msg = state.messages.get(msgId);
    if (!msg?.toolCalls) continue;

    for (const tc of msg.toolCalls) {
      if (tc.result?.startsWith("Error")) continue;

      if (SEARCH_TOOLS.has(tc.name)) {
        // 从搜索结果中提取链接
        try {
          const results = parseJSON<Record<string, unknown>[]>(tc.result, []);
          if (Array.isArray(results)) {
            for (const r of results) {
              const url = (r.url as string) ?? "";
              if (!url || r.type === "image" || seen.has(url)) continue;
              seen.add(url);
              refs.push({
                url,
                title: (r.title as string) ?? extractDomain(url),
                domain: extractDomain(url),
              });
            }
          }
        } catch {
          // 忽略解析失败
        }
      } else if (CRAWL_TOOLS.has(tc.name)) {
        // 从爬虫结果中提取链接
        const crawlUrl = (tc.args as { url?: string }).url ?? "";
        try {
          const result = JSON.parse(tc.result!) as Record<string, unknown>;
          const url = (result.url as string) ?? crawlUrl;
          if (url && !seen.has(url)) {
            seen.add(url);
            const title =
              (result.title as string) && result.title !== "未命名文档"
                ? (result.title as string)
                : extractDomain(url);
            refs.push({ url, title, domain: extractDomain(url) });
          }
        } catch {
          if (crawlUrl && !seen.has(crawlUrl)) {
            seen.add(crawlUrl);
            refs.push({
              url: crawlUrl,
              title: extractDomain(crawlUrl),
              domain: extractDomain(crawlUrl),
            });
          }
        }
      }
    }
  }

  return refs;
}

// ── 组件 ──────────────────────────────────────────

export interface ReportReferencesProps {
  researchId: string;
  className?: string;
}

export function ReportReferences({
  researchId,
  className,
}: ReportReferencesProps) {
  const references = useMemo(
    () => extractReferences(researchId),
    [researchId],
  );

  if (references.length === 0) return null;

  return (
    <div className={cn("mt-8 border-t pt-6", className)}>
      {/* 标题 */}
      <div className="mb-4 flex items-center gap-2 text-sm font-semibold text-foreground">
        <BookOpen className="h-4 w-4" />
        <span>参考资料</span>
        <span className="text-xs font-normal text-muted-foreground">
          ({references.length})
        </span>
      </div>

      {/* 参考资料列表 */}
      <ol className="flex flex-col gap-2">
        {references.map((ref, i) => (
          <li key={ref.url} className="group flex items-start gap-2 text-sm">
            {/* 序号 */}
            <span className="mt-0.5 shrink-0 text-xs text-muted-foreground/60 tabular-nums">
              [{i + 1}]
            </span>

            {/* favicon + 链接 */}
            <a
              href={ref.url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex min-w-0 flex-1 items-center gap-2 rounded-md px-2 py-1.5 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
            >
              <FavIcon
                url={ref.url}
                className="h-4 w-4 shrink-0"
                title={ref.title}
              />
              <span className="truncate">{ref.title}</span>
              <span className="shrink-0 text-xs text-muted-foreground/50">
                {ref.domain}
              </span>
              <ExternalLink className="ml-auto h-3 w-3 shrink-0 opacity-0 transition-opacity group-hover:opacity-50" />
            </a>
          </li>
        ))}
      </ol>
    </div>
  );
}
