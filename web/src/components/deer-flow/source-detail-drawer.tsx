"use client";

import { ExternalLink, Globe, FileText } from "lucide-react";

import { useSourceStore } from "~/core/source-store";
import { Button } from "~/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
  SheetFooter,
} from "~/components/ui/sheet";

import { FavIcon } from "./fav-icon";

// ── 工具函数 ──────────────────────────────────────

/** 从 URL 提取域名 */
function extractDomain(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return url;
  }
}

// ── 组件 ──────────────────────────────────────────

/**
 * 来源详情抽屉组件
 *
 * 从 useSourceStore 读取当前选中来源，以侧边 Sheet 的形式展示详情。
 * 支持：标题、域名、摘要、全文预览、AI 摘要、外部链接跳转。
 */
export function SourceDetailDrawer() {
  const drawerOpen = useSourceStore((s) => s.drawerOpen);
  const closeDrawer = useSourceStore((s) => s.closeDrawer);
  const selectedUrl = useSourceStore((s) => s.selectedUrl);
  const references = useSourceStore((s) => s.references);

  // 按 URL 查找匹配的来源数据
  const source = selectedUrl
    ? references.find((r) => r.url === selectedUrl)
    : null;

  const domain = source?.domain ?? (selectedUrl ? extractDomain(selectedUrl) : "");
  const title = source?.title ?? domain ?? "来源详情";

  return (
    <Sheet open={drawerOpen} onOpenChange={(open) => !open && closeDrawer()}>
      <SheetContent side="right" className="w-[400px] sm:max-w-[400px] overflow-y-auto">
        <SheetHeader>
          <div className="flex items-center gap-2">
            {selectedUrl ? (
              <FavIcon url={selectedUrl} className="h-5 w-5 shrink-0" title={title} />
            ) : (
              <Globe className="h-5 w-5 shrink-0 text-muted-foreground" />
            )}
            <SheetTitle className="line-clamp-2 text-base">{title}</SheetTitle>
          </div>
          <SheetDescription className="text-xs text-muted-foreground">
            {domain}
          </SheetDescription>
        </SheetHeader>

        {/* 内容区域 */}
        <div className="flex flex-1 flex-col gap-4 px-4">
          {/* 来源类型标识 */}
          {source?.sourceType && (
            <div className="flex items-center gap-1.5">
              <span className="inline-flex items-center rounded-full bg-muted px-2 py-0.5 text-xs text-muted-foreground">
                {source.sourceType === "search" && "搜索结果"}
                {source.sourceType === "crawl" && "网页爬取"}
                {source.sourceType === "knowledge" && "知识库"}
              </span>
              {source.toolName && (
                <span className="text-xs text-muted-foreground/60">
                  via {source.toolName}
                </span>
              )}
            </div>
          )}

          {/* AI 摘要 */}
          {source?.aiSummary && (
            <div className="rounded-md border bg-muted/30 p-3">
              <p className="mb-1 text-xs font-medium text-muted-foreground">AI 摘要</p>
              <p className="text-sm leading-relaxed">{source.aiSummary}</p>
            </div>
          )}

          {/* 内容摘要/片段 */}
          {source?.snippet && (
            <div>
              <p className="mb-1 text-xs font-medium text-muted-foreground">内容摘要</p>
              <p className="text-sm leading-relaxed text-foreground/80">
                {source.snippet.length > 500
                  ? source.snippet.slice(0, 500) + "..."
                  : source.snippet}
              </p>
            </div>
          )}

          {/* 全文预览 */}
          {source?.fullContent && !source?.snippet && (
            <div>
              <p className="mb-1 text-xs font-medium text-muted-foreground">全文预览</p>
              <p className="text-sm leading-relaxed text-foreground/80">
                {source.fullContent.length > 800
                  ? source.fullContent.slice(0, 800) + "..."
                  : source.fullContent}
              </p>
            </div>
          )}

          {/* 无详细数据时的简化视图 */}
          {!source && selectedUrl && (
            <div className="flex flex-col items-center justify-center gap-3 py-8 text-center">
              <FileText className="h-10 w-10 text-muted-foreground/40" />
              <p className="text-sm text-muted-foreground">
                暂无该来源的详细信息
              </p>
              <p className="text-xs text-muted-foreground/60">
                可点击下方按钮访问原始链接
              </p>
            </div>
          )}
        </div>

        {/* 底部操作栏 */}
        <SheetFooter>
          {selectedUrl && (
            <Button
              variant="outline"
              className="w-full gap-2"
              onClick={() => window.open(selectedUrl, "_blank", "noopener,noreferrer")}
            >
              <ExternalLink className="h-4 w-4" />
              打开原始链接
            </Button>
          )}
        </SheetFooter>
      </SheetContent>
    </Sheet>
  );
}
