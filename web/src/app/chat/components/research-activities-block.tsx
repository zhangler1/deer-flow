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
import { parseThinkTags } from "~/core/utils/think-tag-parser";
import { cn } from "~/lib/utils";

// ── 搜索结果类型 ──────────────────────────────────

type SearchResult = {
  type?: string;
  title?: string;
  url?: string;
  content?: string;
  image_url?: string;
  image_description?: string;
  // —— 内网知识库类检索结果常无 url，充当“不可点文档”展示的关键字段 ——
  source?: string;
  docGuid?: string;
};

// ── 爬虫结果类型 ──────────────────────────────────

type CrawlResult = {
  title?: string;
  url?: string;
  preview?: string;
  summary?: string;
};

// ── Plan 类型定义 ──────────────────────────────────

type PlanStep = {
  title: string;
  description: string;
  need_search: boolean;
  step_type: string;
  execution_res?: string | null;
};

type Plan = {
  locale: string;
  has_enough_context: boolean;
  thought: string;
  title: string;
  steps: PlanStep[];
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

/** 从 Markdown 内容中提取摘要（--- 之前的第一段纯文本） */
function extractSummary(content: string): string {
  if (!content) return "";
  // 按 --- 分隔，只取前面的摘要部分
  const separatorIndex = content.indexOf("\n---");
  const summary = separatorIndex > 0 ? content.slice(0, separatorIndex) : content;
  // 去掉 Markdown 标题标记（# 开头行），只保留纯文本
  const lines = summary
    .split("\n")
    .map((line) => line.replace(/^#+\s*/, "").trim())
    .filter((line) => line.length > 0);
  return lines.join(" ").trim();
}

/** 判断是否为搜索类工具 */
function isSearchTool(name: string): boolean {
  return [
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
    "local_search_tool",
    "retriever_tool",
    "research_skill_prompt_search",
    "vector_search",
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
    // research_skill_prompt_search 返回纯 markdown，不是 JSON，跳过解析
    if (toolCall.result && toolCall.name !== "research_skill_prompt_search") {
      try {
        console.log('[ResearchActivity] 解析搜索结果 | tool=', toolCall.name, '| result=', toolCall.result?.substring(0, 300));
        const results = parseJSON<SearchResult[]>(toolCall.result, []);
        console.log('[ResearchActivity] 解析结果 | 数量=', results?.length, '| 第一条=', results?.[0]);
        if (Array.isArray(results)) {
          let docCount = 0; // 限制无URL文档卡片的显示数量
          results
            .filter((r) => r.type !== "image")
            .slice(0, 5)
            .forEach((r) => {
              if (r.url) {
                console.log('[ResearchActivity] 构建 SourceLink | url=', r.url, '| title=', r.title, '| source=', r.source);
                tags.push({
                  type: "source",
                  url: r.url,
                  domain: extractDomain(r.url),
                  title: r.title || undefined,
                });
              } else if ((r.title || r.source) && docCount < 5) {
                // 无 URL 的内网知识库类结果，使用不可点文档卡片展示
                tags.push({
                  type: "doc",
                  title: r.source ?? r.title ?? "未命名文档",
                  subtitle: r.source && r.title ? r.title : undefined,
                });
                docCount += 1;
              }
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
            title: result.title || undefined,
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
  isCompleted: boolean = false,
  isReportGenerating: boolean = false,
): { steps: ThinkingStep[]; title: string } {
  const steps: ThinkingStep[] = [];
  let title = "深度研究";
  let planSteps: PlanStep[] = [];

  // 收集非 reporter/planner 的 researcher 消息
  const researcherMessages: import("~/core/messages/types").Message[] = [];

  for (let i = 0; i < activityIds.length; i++) {
    const messageId = activityIds[i]!;
    const message = getMessage(messageId);
    if (!message) continue;

    // planner 消息：解析 Plan JSON 获取 title 和 steps
    if (message.agent === "planner") {
      const plan = parseJSON<Plan | null>(message.content, null);
      if (plan) {
        title = plan.title || "深度研究";
        planSteps = plan.steps || [];
      }
      continue;
    }

    // 跳过 reporter 消息
    if (message.agent === "reporter") continue;

    // 跳过第一条（research 本身，通常无内容）
    if (i === 0) continue;

    // 收集 researcher 消息
    researcherMessages.push(message);
  }

  // 以 researcher 消息为主驱动，利用后端传入的 stepIndex 控制展示层级
  // 优先使用后端传入的 stepIndex，当 stepIndex 缺失时按 planSteps 顺序推导
  let lastStepIndex = -1;

  // 跟踪已展示的 plan step，确保每个 step 至少显示一次标题行
  const shownPlanSteps = new Set<number>();

  for (const msg of researcherMessages) {
    const rawContent = msg.content || "";

    // 解析 think tag：分离思考内容和正文
    const { thinkingContent, mainContent } = parseThinkTags(rawContent);
    // 描述仅使用正文内容（过滤掉 think tag）
    const description = extractSummary(mainContent);

    // 提取工具调用标签
    const toolCallTags: ToolCallTag[] = [];
    if (msg.toolCalls) {
      for (const tc of msg.toolCalls) {
        if (tc.result?.startsWith("Error")) continue;
        toolCallTags.push(...extractToolCallTags(tc));
      }
    }

    if (!description && toolCallTags.length === 0) continue;

    // 优先使用后端传入的 stepIndex
    // 当 stepIndex 缺失时（如最后一步 updates 时序问题），按顺序推导
    let msgStepIndex = msg.stepIndex;
    const msgStepTitle = msg.stepTitle;

    // Fallback: 如果后端没有传 stepIndex，基于 lastStepIndex 推导
    // 这是处理最后一步 updates 事件时序竞争的保底逻辑
    if (msgStepIndex === undefined && lastStepIndex >= 0 && lastStepIndex < planSteps.length - 1) {
      msgStepIndex = lastStepIndex + 1;
    }

    // 如果进入新的 step，先展示 plan step 标题行
    if (msgStepIndex !== undefined && msgStepIndex !== lastStepIndex) {
      lastStepIndex = msgStepIndex;
      const currentPlanStep = planSteps[msgStepIndex];
      const stepTitle = msgStepTitle || currentPlanStep?.title;
      if (stepTitle && !shownPlanSteps.has(msgStepIndex)) {
        shownPlanSteps.add(msgStepIndex);
        steps.push({
          id: `plan-${msgStepIndex}`,
          description: stepTitle,
          toolCalls: [],
          isPlanStep: true,
        });
      }
    }

    // Research 活动行（缩进在 plan step 下）
    steps.push({
      id: msg.id,
      description: description
        || (msgStepIndex !== undefined ? planSteps[msgStepIndex]?.description : undefined)
        || (toolCallTags.length > 0 ? "执行搜索与资料阅读" : ""),
      toolCalls: toolCallTags,
      thinkingContent: thinkingContent || undefined,
    });
  }

  // 报告生成中，追加提示步骤
  if (isReportGenerating && !isCompleted && steps.length > 0) {
    steps.push({
      id: "report-generating-step",
      title: undefined,
      description: "研究报告生成中",
      toolCalls: [],
    });
  }

  // 研究完成后，追加收尾步骤
  if (isCompleted && steps.length > 0) {
    steps.push({
      id: "completion-step",
      title: undefined,
      description: "已搜集和分析资料",
      toolCalls: [],
      isCompleted: true,
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
  // 报告已完成时，确保不再显示 loading
  const reportId = useStore((state) =>
    researchId ? state.researchReportIds.get(researchId) : undefined,
  );
  const reportCompleted = useStore((state) => {
    if (!reportId) return false;
    const report = state.messages.get(reportId);
    return report ? !report.isStreaming && !!report.content : false;
  });
  const reportGenerating = useStore((state) => {
    if (!reportId) return false;
    const report = state.messages.get(reportId);
    return report ? !!report.isStreaming : false;
  });
  const showLoading = ongoing && !reportCompleted;

  // 订阅 researcher 消息的 stepIndex 变化，确保流式更新时重新渲染
  const stepIndexDeps = useStore((state) => {
    const ids = state.researchActivityIds.get(researchId) || [];
    const indices: number[] = [];
    for (const id of ids) {
      const msg = state.messages.get(id);
      if (msg?.agent === "researcher" && msg.stepIndex !== undefined) {
        indices.push(msg.stepIndex);
      }
    }
    return indices.join(",");
  });

  // 订阅 toolCall.result 变化，确保搜索结果到达后立即重新渲染胶囊
  const toolCallResultDeps = useStore((state) => {
    const ids = state.researchActivityIds.get(researchId) || [];
    let resultCount = 0;
    for (const id of ids) {
      const msg = state.messages.get(id);
      if (msg?.toolCalls) {
        for (const tc of msg.toolCalls) {
          if (tc.result) resultCount++;
        }
      }
    }
    return resultCount;
  });

  const { steps, title } = useMemo(() => {
    const state = useStore.getState();
    return buildStepsFromActivityIds(
      activityIds,
      (id) => state.messages.get(id),
      reportCompleted,
      reportGenerating,
    );
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activityIds, reportCompleted, reportGenerating, stepIndexDeps, toolCallResultDeps]);

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
      {showLoading && <LoadingAnimation className="mx-4 my-12" />}
    </div>
  );
}
