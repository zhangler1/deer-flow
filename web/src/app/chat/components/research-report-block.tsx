// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

import { useCallback, useEffect, useRef } from "react";

import { extractSourceDetails } from "~/app/chat/components/report-references";
import { LoadingAnimation } from "~/components/deer-flow/loading-animation";
import { SourceAwareMarkdown } from "~/components/deer-flow/source-aware-markdown";
import { SourceDetailDrawer } from "~/components/deer-flow/source-detail-drawer";
import ReportEditor from "~/components/editor";
import { useReplay } from "~/core/replay";
import { useSourceStore } from "~/core/source-store";
import { useMessage, useStore } from "~/core/store";
import { stripThinkTags } from "~/core/utils/think-tag-parser";
import { cn } from "~/lib/utils";

import { CollapsibleReport } from "./collapsible-report";
import { ReportReferences } from "./report-references";

// ── URL 归一化 ──────────────────────────────────────

/** 去掉 fragment 与常见追踪 query，生成用于跨数据源匹配的“指纹 key” */
function normalizeUrlForMatch(url: string): string {
  try {
    const u = new URL(url);
    // 对所有域名去掉 fragment 和常见追踪参数
    const TRACKING_PARAMS = new Set([
      "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
      "ref", "source", "from",
    ]);
    const params = Array.from(u.searchParams.entries())
      .filter(([k]) => !TRACKING_PARAMS.has(k.toLowerCase()))
      .sort(([a], [b]) => a.localeCompare(b));
    const qs = params.length > 0 ? "?" + params.map(([k, v]) => `${k}=${v}`).join("&") : "";
    // klbs 域名额外去掉全部 query，只保留 origin + pathname
    if (/^klbs-.*\.bocomm\.com$/.test(u.hostname)) {
      return u.origin + u.pathname;
    }
    return u.origin + u.pathname + qs;
  } catch {
    return url;
  }
}

/** 标题规范化（用于跨数据源匹配） */
function normalizeTitleKey(title: string, domain: string): string {
  const t = title.trim().toLowerCase().replace(/\s+/g, " ");
  const d = domain.trim().toLowerCase();
  return `${d}::${t}`;
}

// ── 组件 ────────────────────────────────────────────

export function ResearchReportBlock({
  className,
  researchId,
  messageId,
  editing,
  allExpanded,
}: {
  className?: string;
  researchId: string;
  messageId: string;
  editing: boolean;
  allExpanded: boolean;
}) {
  const message = useMessage(messageId);
  const { isReplay } = useReplay();
  const setReferences = useSourceStore((s) => s.setReferences);
  const setResearchId = useSourceStore((s) => s.setResearchId);
  const isCompleted = message?.isStreaming === false && message?.content !== "";

  // 提取来源数据并设置到 store
  // 优先使用后端通过 reference_index SSE 事件设置的数据（与 MD 参考文献一致）
  // 同时从 tool_call_result 中提取 snippet 等内容字段，合并补充到已有数据中
  useEffect(() => {
    setResearchId(researchId);
    const currentRefs = useSourceStore.getState().references;
    const toolCallSources = extractSourceDetails(researchId);

    if (currentRefs.length > 0) {
      // 后端 reference_index 已提供 url/title/domain，但缺少 snippet/fullContent/aiSummary
      // 从 toolCall 结果中补充内容字段
      // 匹配策略（优先级递减）：
      //   a) url 精确匹配
      //   b) url 归一化匹配（去掉 fragment / 常见追踪参数 / klbs 去全部 query）
      //   c) domain+title 规范化匹配（处理 LLM 改写 URL 的情况）
      const contentByUrl = new Map<string, (typeof toolCallSources)[number]>();
      const contentByNormUrl = new Map<string, (typeof toolCallSources)[number]>();
      const contentByTitle = new Map<string, (typeof toolCallSources)[number]>();
      for (const s of toolCallSources) {
        if (s.url) {
          contentByUrl.set(s.url, s);
          const norm = normalizeUrlForMatch(s.url);
          if (!contentByNormUrl.has(norm)) contentByNormUrl.set(norm, s);
        }
        if (s.title || s.domain) {
          const key = normalizeTitleKey(s.title || "", s.domain || "");
          if (!contentByTitle.has(key)) contentByTitle.set(key, s);
        }
      }
      const enriched = currentRefs.map((ref) => {
        if (!ref.url) return ref;
        const detail = contentByUrl.get(ref.url)
          ?? contentByNormUrl.get(normalizeUrlForMatch(ref.url))
          ?? contentByTitle.get(normalizeTitleKey(ref.title || "", ref.domain || ""));
        if (detail && (!ref.snippet && !ref.fullContent)) {
          return {
            ...ref,
            snippet: detail.snippet,
            fullContent: detail.fullContent,
            aiSummary: detail.aiSummary,
            toolName: detail.toolName ?? ref.toolName,
            sourceType: detail.sourceType ?? ref.sourceType,
          };
        }
        return ref;
      });
      console.log('[ResearchReportBlock] 合并后端 reference_index + toolCall 内容 | 条数:', enriched.length);
      setReferences(enriched);
      return;
    }
    // Fallback: 后端未提供 reference_index，完全从 tool_call_result 中提取
    console.log('[ResearchReportBlock] Fallback: 从 toolCalls 提取来源 | 条数:', toolCallSources.length);
    setReferences(toolCallSources);
  }, [researchId, setResearchId, setReferences, isCompleted]);

  const references = useSourceStore((s) => s.references);

  const handleMarkdownChange = useCallback(
    (markdown: string) => {
      if (message) {
        // 创建新的 message 对象以确保触发响应式更新
        const updatedMessage = { ...message, content: markdown };
        
        // 更新 store
        const currentMessages = useStore.getState().messages;
        const newMessages = new Map(currentMessages);
        newMessages.set(message.id, updatedMessage);
        
        useStore.setState({
          messages: newMessages,
        });
      }
    },
    [message],
  );
  const contentRef = useRef<HTMLDivElement>(null);

  // reporter 内容过滤 think tag：流式和已完成均过滤
  const filteredContent = stripThinkTags(message?.content ?? "");
  // 编辑器内容：也过滤 think tag
  const editorContent = stripThinkTags(message?.content ?? "");

  // 流式场景：如果过滤后无正文内容（仅含未闭合的 think tag），不渲染任何内容
  const hasDisplayContent = message?.isStreaming ? filteredContent.length > 0 : true;

  // TODO: scroll to top when completed, but it's not working
  // useEffect(() => {
  //   if (isCompleted && contentRef.current) {
  //     setTimeout(() => {
  //       contentRef
  //         .current!.closest("[data-radix-scroll-area-viewport]")
  //         ?.scrollTo({
  //           top: 0,
  //           behavior: "smooth",
  //         });
  //     }, 500);
  //   }
  // }, [isCompleted]);

  return (
    <div ref={contentRef} className={cn("w-full min-w-0 overflow-hidden pt-4 pb-8", className)}>
      {!isReplay && isCompleted && editing ? (
        <ReportEditor
          content={editorContent}
          onMarkdownChange={handleMarkdownChange}
        />
      ) : (
        <>
          {/* 流式输出时用 SourceAwareMarkdown（支持打字动画 + 源引用角标） */}
          {message?.isStreaming ? (
            hasDisplayContent ? (
              <SourceAwareMarkdown animated checkLinkCredibility references={references}>
                {filteredContent}
              </SourceAwareMarkdown>
            ) : null
          ) : (
            <CollapsibleReport
              content={filteredContent}
              checkLinkCredibility
              references={references}
              allExpanded={allExpanded}
            />
          )}
          {message?.isStreaming && <LoadingAnimation className="my-12" />}
          {/* 报告完成后展示参考资料 */}
          {isCompleted && <ReportReferences researchId={researchId} />}
          {/* 来源详情抽屉 */}
          <SourceDetailDrawer />
        </>
      )}
    </div>
  );
}
