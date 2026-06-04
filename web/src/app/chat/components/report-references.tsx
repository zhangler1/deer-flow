"use client";

import { ExternalLink, Globe, BookOpen } from "lucide-react";
import { useCallback, useMemo } from "react";

import { FavIcon } from "~/components/deer-flow/fav-icon";
import { useSourceStore } from "~/core/source-store";
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

/** 来源详细信息（用于溯源详情页） */
export interface SourceDetail {
  url: string;
  title: string;
  domain: string;
  snippet?: string;
  fullContent?: string;
  aiSummary?: string;
  sourceType: "search" | "crawl" | "knowledge";
  toolName?: string;
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
  "bocomsearch",
  "budget_controlled_bocomsearch",
  "searchknowledge_standard",
  "budget_controlled_searchknowledge_standard",
  "industry_report_search",
  "product_search",
  "product_instance_search",
  "news_search",
  "news_detail_search",
]);

/** 爬虫工具名列表 */
const CRAWL_TOOLS = new Set(["crawl_tool", "batch_crawl_tool"]);

/** 从 researchId 对应的所有 activity 消息中提取参考资料 */
export function extractReferences(
  researchId: string,
): ReferenceItem[] {
  return extractSourceDetails(researchId).map(s => ({ url: s.url, title: s.title, domain: s.domain }));
}

/** 从 researchId 对应的所有 activity 消息中提取完整来源数据 */
export function extractSourceDetails(
  researchId: string,
): SourceDetail[] {
  const state = useStore.getState();
  const activityIds = state.researchActivityIds.get(researchId);
  if (!activityIds) {
    console.warn('[ReportReferences] researchActivityIds 无映射, researchId=', researchId);
    return [];
  }
  console.log('[ReportReferences] activityIds:', activityIds.length, '条消息');

  const seen = new Set<string>();
  const sources: SourceDetail[] = [];

  for (const msgId of activityIds) {
    const msg = state.messages.get(msgId);
    if (!msg?.toolCalls) continue;

    for (const tc of msg.toolCalls) {
      console.log('[ReportReferences] toolCall:', tc.name, '| result长度:', tc.result?.length ?? 0);
      if (tc.result?.startsWith("Error")) continue;

      if (SEARCH_TOOLS.has(tc.name)) {
        // 从搜索结果中提取链接/文档
        try {
          const results = parseJSON<Record<string, unknown>[]>(tc.result, []);
          if (Array.isArray(results)) {
            for (const r of results) {
              if (r.type === "image") continue;
              const url = (r.url as string) ?? "";
              if (url) {
                if (seen.has(url)) continue;
                seen.add(url);
                sources.push({
                  url,
                  title: (r.title as string) ?? extractDomain(url),
                  domain: extractDomain(url),
                  snippet: (r.content as string) ?? "",
                  sourceType: "search",
                  toolName: tc.name,
                });
              } else {
                // —— 无 URL 的内网知识库结果，用 docGuid 去重，不渲染跳转 ——
                const docGuid = (r.docGuid as string) ?? "";
                const source = (r.source as string) ?? "";
                const title = (r.title as string) ?? source;
                const key = `doc:${docGuid || source || title}`;
                if (!key || key === "doc:" || seen.has(key)) continue;
                if (!title && !source) continue;
                seen.add(key);
                sources.push({
                  url: "",  // 空 URL 表示不可点
                  title: title || source || "未命名文档",
                  domain: source || "内部文档",
                  snippet: (r.content as string) ?? "",
                  sourceType: "knowledge",
                  toolName: tc.name,
                });
              }
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
            sources.push({
              url,
              title,
              domain: extractDomain(url),
              snippet: (result.preview as string) ?? "",
              aiSummary: (result.summary as string) ?? undefined,
              fullContent: (result.content as string) ?? undefined,
              sourceType: "crawl",
              toolName: tc.name,
            });
          }
        } catch {
          if (crawlUrl && !seen.has(crawlUrl)) {
            seen.add(crawlUrl);
            sources.push({
              url: crawlUrl,
              title: extractDomain(crawlUrl),
              domain: extractDomain(crawlUrl),
              sourceType: "crawl",
              toolName: tc.name,
            });
          }
        }
      }
    }
  }

  return sources;
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
  // 优先使用 source-store 中的数据（由后端 reference_index SSE 事件设置，与 MD 参考文献一致）
  const storeReferences = useSourceStore((s) => s.references);
  const references: ReferenceItem[] = useMemo(() => {
    if (storeReferences.length > 0) {
      // 后端已提供 reference_index，直接使用
      return storeReferences.map(s => ({ url: s.url, title: s.title, domain: s.domain }));
    }
    // Fallback: 从 tool_call_result 中提取
    return extractReferences(researchId);
  }, [storeReferences, researchId]);
  const openSourceByUrl = useSourceStore((s) => s.openSourceByUrl);

  const handleClick = useCallback(
    (e: React.MouseEvent, url: string) => {
      e.preventDefault();
      e.stopPropagation();
      // Ctrl/Cmd+Click → 直接在新标签页打开
      if (e.ctrlKey || e.metaKey) {
        window.open(url, "_blank", "noopener,noreferrer");
        return;
      }
      // 普通点击 → 打开 Drawer
      openSourceByUrl(url);
    },
    [openSourceByUrl],
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
          <li key={`${ref.url}-${ref.title}-${i}`} className="group flex items-start gap-2 text-sm">
            {/* 序号 */}
            <span className="mt-0.5 shrink-0 text-xs text-muted-foreground/60 tabular-nums">
              [{i + 1}]
            </span>

            {ref.url ? (
              /* 有 URL：favicon + 可点击打开 Drawer */
              <div
                role="button"
                tabIndex={0}
                onClick={(e) => handleClick(e, ref.url)}
                className="flex min-w-0 flex-1 cursor-pointer items-center gap-2 rounded-md px-2 py-1.5 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
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
              </div>
            ) : (
              /* 无 URL：不可点文档卡片 */
              <div
                className="flex min-w-0 flex-1 items-center gap-2 rounded-md px-2 py-1.5 text-muted-foreground"
                title={ref.title}
              >
                <BookOpen className="h-4 w-4 shrink-0" />
                <span className="truncate">{ref.title}</span>
                <span className="shrink-0 text-xs text-muted-foreground/50">
                  {ref.domain}
                </span>
              </div>
            )}
          </li>
        ))}
      </ol>
    </div>
  );
}
