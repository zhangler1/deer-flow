"use client";

import { motion } from "framer-motion";
import { useMemo } from "react";

import { LoadingAnimation } from "~/components/deer-flow/loading-animation";
import {
  ReferenceSteps,
  type ThinkingStep,
  type ToolCallTag,
} from "~/components/deer-flow/reference-steps";
import type { ToolCallRuntime } from "~/core/messages";
import { useMessage, useStore } from "~/core/store";
import { parseJSON } from "~/core/utils";
import { cn } from "~/lib/utils";

// ── 搜索结果类型 ──────────────────────────────────

type SearchResult = {
  type?: string;
  title?: string;
  url?: string;
  content?: string;
  image_url?: string;
  image_description?: string;
};

// ── 爬虫结果类型 ──────────────────────────────────

type CrawlResult = {
  title?: string;
  url?: string;
  preview?: string;
  summary?: string;
};

// ── 辅助函数 ──────────────────────────────────────

/** 从 URL 提取域名 */
function extractDomain(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return url;
  }
}

/** 判断是否为搜索类工具 */
function isSearchTool(name: string): boolean {
  return [
    "web_search",
    "domain_fin_search",
    "online_search",
    "industry_report_search",
    "product_search",
    "product_instance_search",
    "news_search",
    "news_detail_search",
    "local_search_tool",
    "retriever_tool",
    "research_skill_prompt_search",
  ].includes(name);
}

/** 判断是否为爬虫类工具 */
function isCrawlTool(name: string): boolean {
  return ["crawl_tool", "batch_crawl_tool"].includes(name);
}

// ── 从 ToolCall 提取标签 ──────────────────────────

function extractToolCallTags(toolCall: ToolCallRuntime): ToolCallTag[] {
  const tags: ToolCallTag[] = [];

  if (isSearchTool(toolCall.name)) {
    // 搜索关键词标签
    const query =
      (toolCall.args as { query?: string; keywords?: string; keyword?: string })
        .query ??
      (toolCall.args as { keywords?: string }).keywords ??
      (toolCall.args as { keyword?: string }).keyword ??
      "";
    if (query) {
      tags.push({ type: "search", query });
    }

    // 来源链接（从搜索结果中提取前 N 条）
    if (toolCall.result) {
      try {
        const results = parseJSON<SearchResult[]>(toolCall.result, []);
        if (Array.isArray(results)) {
          results
            .filter((r) => r.type !== "image" && r.url)
            .slice(0, 5)
            .forEach((r) => {
              tags.push({
                type: "source",
                url: r.url!,
                domain: extractDomain(r.url!),
              });
            });
        }
      } catch {
        // 解析失败忽略
      }
    }
  } else if (isCrawlTool(toolCall.name)) {
    // 爬虫：已阅读标签 + 来源链接
    const url = (toolCall.args as { url?: string }).url ?? "";
    if (toolCall.result) {
      tags.push({ type: "read" });
      // 从爬虫结果中提取来源
      try {
        const result = JSON.parse(toolCall.result) as CrawlResult;
        const resultUrl = result.url ?? url;
        if (resultUrl) {
          tags.push({
            type: "source",
            url: resultUrl,
            domain: extractDomain(resultUrl),
          });
        }
      } catch {
        if (url) {
          tags.push({ type: "source", url, domain: extractDomain(url) });
        }
      }
    }
  } else {
    // 其他 MCP 工具：显示工具名称标签
    const toolLabel = toolCall.name || "工具调用";
    tags.push({ type: "read", label: `已执行: ${toolLabel}` });
  }

  return tags;
}

// ── 从消息列表构建步骤 ────────────────────────────

function buildStepsFromActivityIds(
  activityIds: string[],
  getMessage: (id: string) => import("~/core/messages/types").Message | undefined,
): { steps: ThinkingStep[]; title: string } {
  const steps: ThinkingStep[] = [];
  let title = "深度研究";

  for (let i = 0; i < activityIds.length; i++) {
    const messageId = activityIds[i]!;
    const message = getMessage(messageId);
    if (!message) continue;

    // 第一条消息的 content 作为标题
    if (i === 0 && message.content) {
      title = message.content.slice(0, 50) || "深度研究";
      continue;
    }

    // 跳过 reporter 和 planner 的消息
    if (message.agent === "reporter" || message.agent === "planner") continue;

    // 构建步骤描述
    const description = message.content || "";
    if (!description && !message.toolCalls?.length) continue;

    // 提取工具调用标签
    const toolCallTags: ToolCallTag[] = [];
    if (message.toolCalls) {
      for (const tc of message.toolCalls) {
        if (tc.result?.startsWith("Error")) continue;
        toolCallTags.push(...extractToolCallTags(tc));
      }
    }

    steps.push({
      id: messageId,
      title: undefined, // 不显示步骤小标题，保持简洁
      description: description || (toolCallTags.length > 0 ? "执行搜索与资料阅读" : ""),
      toolCalls: toolCallTags,
    });
  }

  return { steps, title };
}

// ── 主组件 ────────────────────────────────────────

export function ResearchActivitiesBlock({
  className,
  researchId,
}: {
  className?: string;
  researchId: string;
}) {
  const activityIds = useStore((state) =>
    state.researchActivityIds.get(researchId),
  )!;
  const ongoing = useStore(
    (state) => state.ongoingResearchId === researchId,
  );

  const { steps, title } = useMemo(() => {
    const state = useStore.getState();
    return buildStepsFromActivityIds(activityIds, (id) =>
      state.messages.get(id),
    );
  }, [activityIds]);

  if (steps.length === 0) {
    return ongoing ? (
      <LoadingAnimation className="mx-4 my-12" />
    ) : null;
  }

  return (
    <div className={cn("py-4", className)}>
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, ease: "easeOut" }}
      >
        <ReferenceSteps
          title={title}
          steps={steps}
          maxVisibleSources={3}
        />
      </motion.div>
      {ongoing && <LoadingAnimation className="mx-4 my-12" />}
    </div>
  );
}
