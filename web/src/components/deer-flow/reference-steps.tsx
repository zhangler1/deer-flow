"use client";

import { Search, BookOpen, ChevronDown, CheckCircle, FileText, ExternalLink } from "lucide-react";
import { useState, useRef, useCallback } from "react";

import { FavIcon } from "~/components/deer-flow/fav-icon";
import { cn } from "~/lib/utils";

// ── 数据类型 ──────────────────────────────────────────

/** 搜索关键词标签 */
export interface SearchTag {
  type: "search";
  /** 搜索关键词 */
  query: string;
}

/** 已阅读资料标签 */
export interface ReadTag {
  type: "read";
  /** 显示文本，默认"已阅读相关资料" */
  label?: string;
}

/** 来源链接标签（可点击） */
export interface SourceLink {
  type: "source";
  /** 来源 URL */
  url: string;
  /** 显示的域名 */
  domain: string;
  /** 网站 favicon URL（可选） */
  favicon?: string;
  /** 文章/页面标题（可选） */
  title?: string;
}

/** 内网文档标签（不可点，用于无 URL 的知识库结果） */
export interface DocTag {
  type: "doc";
  /** 文档标题或文件名 */
  title: string;
  /** 可选：补充说明（一般是段落小标题） */
  subtitle?: string;
}

/** 工具调用标签联合类型 */
export type ToolCallTag = SearchTag | ReadTag | SourceLink | DocTag;

/** 思考步骤 */
export interface ThinkingStep {
  /** 步骤唯一 ID */
  id: string;
  /** 步骤小标题（可选） */
  title?: string;
  /** 步骤描述文字 */
  description: string;
  /** 工具调用标签列表 */
  toolCalls: ToolCallTag[];
  /** 是否为完成收尾步骤（显示对勾图标） */
  isCompleted?: boolean;
  /** 是否为计划步骤标题（加粗显示，作为 research 活动的分组标题） */
  isPlanStep?: boolean;
  /** 思考内容（从 💭... 标签中提取，researcher 阶段差异化展示） */
  thinkingContent?: string;
}

/** ReferenceSteps 组件属性 */
export interface ReferenceStepsProps {
  /** 研究主题标题 */
  title: string;
  /** 思考步骤列表 */
  steps: ThinkingStep[];
  /** 来源链接最大显示数量，超出折叠，默认 3 */
  maxVisibleSources?: number;
  /** 额外 className */
  className?: string;
}

// ── 子组件 ──────────────────────────────────────────

/** 搜索关键词标签 */
function SearchTagBadge({ query }: { query: string }) {
  return (
    <span className="inline-flex max-w-[180px] items-center gap-1 rounded-full border border-border/50 bg-muted/30 px-2 py-0.5 text-xs text-muted-foreground transition-colors hover:bg-muted">
      <Search className="h-3 w-3 shrink-0" />
      <span className="truncate">{query}</span>
    </span>
  );
}

/** 已阅读资料标签 */
function ReadTagBadge({ label = "已阅读相关资料" }: { label?: string }) {
  return (
    <span className="inline-flex max-w-[180px] items-center gap-1 rounded-full border border-border/50 bg-muted/30 px-2 py-0.5 text-xs text-muted-foreground transition-colors hover:bg-muted">
      <BookOpen className="h-3 w-3 shrink-0" />
      <span className="truncate">{label}</span>
    </span>
  );
}

/** 来源链接胶囊（hover 弹出详情） */
function SourceLinkBadge({ url, domain, favicon, title }: SourceLink) {
  const [showCard, setShowCard] = useState(false);
  const hoverTimeout = useRef<ReturnType<typeof setTimeout> | null>(null);
  const leaveTimeout = useRef<ReturnType<typeof setTimeout> | null>(null);

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
      
      if (e.ctrlKey || e.metaKey) {
        window.open(url, "_blank", "noopener,noreferrer");
        return;
      }
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
        aria-label={`查看来源: ${title || domain}`}
      >
        {favicon ? (
          <img
            src={favicon}
            alt=""
            className="h-3.5 w-3.5 shrink-0 rounded-full object-cover"
            onError={(e) => {
              e.currentTarget.style.display = "none";
            }}
          />
        ) : (
          <FavIcon url={url} className="h-3.5 w-3.5 shrink-0" />
        )}
        <span className="truncate max-w-[80px]">{domain}</span>
      </span>

      {/* 弹出卡片（hover 时显示） */}
      {showCard && (
        <span
          className={cn(
            "absolute z-50 left-1/2 -translate-x-1/2 bottom-full mb-2",
            "w-[260px] rounded-lg border border-border/60 bg-popover px-2.5 py-1.5 shadow-md",
            "animate-in fade-in-0 zoom-in-95 duration-150",
            "cursor-pointer",
          )}
          onMouseEnter={handleCardMouseEnter}
          onMouseLeave={handleCardMouseLeave}
          onClick={handleClick}
        >
          {/* favicon + 域名 */}
          <span className="flex items-center gap-1.5">
            {favicon ? (
              <img
                src={favicon}
                alt=""
                className="h-4 w-4 max-h-4 max-w-4 shrink-0 rounded-sm object-contain"
                onError={(e) => {
                  e.currentTarget.style.display = "none";
                }}
              />
            ) : (
              <FavIcon url={url} className="h-4 w-4 shrink-0 rounded-sm" />
            )}
            <span className="text-xs text-muted-foreground truncate leading-none">
              {domain}
            </span>
          </span>
          
          {/* 标题 */}
          {title && (
            <span className="block mt-1 text-sm font-bold leading-snug text-foreground line-clamp-2">
              {title}
            </span>
          )}
        </span>
      )}
    </span>
  );
}

/** 内网文档胶囊（不可点） */
function DocBadge({ title, subtitle }: DocTag) {
  const display = subtitle ? `${title} · ${subtitle}` : title;
  return (
    <span
      className="inline-flex max-w-[120px] items-center gap-1 rounded-full border border-border/50 bg-muted/30 px-2 py-0.5 text-xs text-muted-foreground"
      title={display}
    >
      <BookOpen className="h-3 w-3 shrink-0" />
      <span className="truncate">{title}</span>
    </span>
  );
}

/** 步骤左侧竖线图标 */
function StepIcon({ isLast, isCompleted, isPlanStep }: { isLast: boolean; isCompleted?: boolean; isPlanStep?: boolean }) {
  return (
    <div className="flex shrink-0 flex-col items-center text-muted-foreground/50">
      <div className="flex h-3.5 w-3.5 items-center justify-center">
        {isCompleted ? (
          <CheckCircle className="h-3.5 w-3.5 text-green-500" />
        ) : isPlanStep ? (
          <FileText className="h-3 w-3 text-foreground/70" />
        ) : (
          <div className="h-1.5 w-1.5 rounded-full bg-current" />
        )}
      </div>
      {!isLast && (
        <div className="mt-1 w-px flex-1 bg-border/50" />
      )}
    </div>
  );
}

// ── 主组件 ──────────────────────────────────────────

export function ReferenceSteps({
  title,
  steps,
  maxVisibleSources = 3,
  className,
}: ReferenceStepsProps) {
  return (
    <div className={cn("rounded-xl border bg-card", className)}>
      {/* 标题 */}
      <div className="border-b px-4 py-3">
        <h3 className="truncate text-sm font-medium text-foreground">
          {title}
        </h3>
      </div>

      {/* 步骤列表 */}
      <div className="flex flex-col gap-4 px-4 py-3">
        {steps.map((step, index) => (
          <StepRow
            key={step.id}
            step={step}
            isLast={index === steps.length - 1}
            maxVisibleSources={maxVisibleSources}
          />
        ))}
      </div>
    </div>
  );
}

/** 单个步骤行 */
function StepRow({
  step,
  isLast,
  maxVisibleSources,
}: {
  step: ThinkingStep;
  isLast: boolean;
  maxVisibleSources: number;
}) {
  // 分离搜索/阅读标签和来源链接/文档
  const searchTags = step.toolCalls.filter(
    (t) => t.type === "search" || t.type === "read",
  );
  const sourceLinks = step.toolCalls.filter(
    (t) => t.type === "source",
  ) as SourceLink[];
  const docTags = step.toolCalls.filter(
    (t) => t.type === "doc",
  ) as DocTag[];

  const [expanded, setExpanded] = useState(false);
  // sourceLinks + docTags 合并计算折叠
  const totalLinks = sourceLinks.length + docTags.length;
  const hasMore = totalLinks > maxVisibleSources;
  const visibleSources = expanded || !hasMore
    ? sourceLinks
    : sourceLinks.slice(0, maxVisibleSources);
  const docQuota = Math.max(0, maxVisibleSources - visibleSources.length);
  const visibleDocs = expanded || !hasMore
    ? docTags
    : docTags.slice(0, docQuota);
  const hiddenCount = totalLinks - maxVisibleSources;

  return (
    <div className="flex gap-2">
      {/* 左侧竖线 + 圆点 */}
      <StepIcon isLast={isLast} isCompleted={step.isCompleted} isPlanStep={step.isPlanStep} />

      {/* 右侧内容 */}
      <div className="min-w-0 flex-1">
        {/* 计划步骤标题（加粗，高层级） */}
        {step.isPlanStep ? (
          <div className="text-base font-semibold text-foreground">
            {step.description}
          </div>
        ) : (
          <>
            {/* 步骤小标题 */}
            {step.title && (
              <div className="mb-1 text-sm font-medium text-foreground">
                {step.title}
              </div>
            )}

            {/* 思考内容（来自 💭 标签，blockquote 引用格式展示） */}
            {step.thinkingContent && (
              <blockquote className="mb-2 border-l-3 border-gray-300 pl-3 text-xs leading-relaxed text-gray-400">
                {step.thinkingContent}
              </blockquote>
            )}

            {/* 步骤描述 */}
            <p className="text-sm leading-relaxed text-muted-foreground">
              {step.description}
            </p>

            {/* 工具调用标签 */}
            {(searchTags.length > 0 || sourceLinks.length > 0 || docTags.length > 0) && (
              <div className="mt-2 flex flex-wrap gap-1 overflow-hidden">
                {/* 搜索/阅读标签 */}
                {searchTags.map((tag, i) => {
                  if (tag.type === "search") {
                    return (
                      <SearchTagBadge key={`search-${i}`} query={tag.query} />
                    );
                  }
                  return (
                    <ReadTagBadge key={`read-${i}`} label={tag.label} />
                  );
                })}

                {/* 来源链接 */}
                {visibleSources.map((source, i) => (
                  <SourceLinkBadge key={`source-${i}`} {...source} />
                ))}

                {/* 内网文档胶囊（不可点） */}
                {visibleDocs.map((doc, i) => (
                  <DocBadge key={`doc-${i}`} {...doc} />
                ))}

                {/* 展开/收起按钮 */}
                {hasMore && (
                  <button
                    onClick={() => setExpanded(!expanded)}
                    className="inline-flex items-center gap-1 rounded-full border border-border/50 bg-muted/30 px-2 py-0.5 text-xs text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
                  >
                    <ChevronDown
                      className={cn(
                        "h-3 w-3 transition-transform",
                        expanded && "rotate-180",
                      )}
                    />
                    <span>{expanded ? "收起" : `+${hiddenCount}`}</span>
                  </button>
                )}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
