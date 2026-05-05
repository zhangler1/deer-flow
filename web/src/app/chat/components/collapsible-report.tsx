"use client";

import { ChevronDown } from "lucide-react";
import { useMemo } from "react";

import { Markdown } from "~/components/deer-flow/markdown";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "~/components/ui/accordion";
import { cn } from "~/lib/utils";

// ── 类型 ──────────────────────────────────────────

/** 报告章节 */
interface ReportSection {
  /** 章节唯一标识 */
  id: string;
  /** 标题文本 */
  title: string;
  /** 标题级别 (## = 2, ### = 3) */
  level: number;
  /** 章节内容（不含标题行的 Markdown） */
  content: string;
}

// ── 解析逻辑 ──────────────────────────────────────

/**
 * 将 Markdown 文本按 ## 标题拆分为章节
 * 
 * 逻辑：
 * - 顶级标题（# 开头）作为报告总标题，单独渲染
 * - 二级标题（## 开头）作为章节标题，每个章节可折叠
 * - 三级及以下标题保留在章节内容中，不单独拆分
 */
function parseReportSections(markdown: string): {
  preamble: string;
  sections: ReportSection[];
} {
  const lines = markdown.split("\n");
  const sections: ReportSection[] = [];
  let preamble = ""; // 标题之前的内容
  let currentSection: ReportSection | null = null;
  let foundFirstH2 = false;
  let preambleLines: string[] = [];

  for (const line of lines) {
    // 匹配 ## 标题（二级）
    const h2Match = line.match(/^##\s+(.+)/);
    
    if (h2Match) {
      foundFirstH2 = true;
      // 保存之前的章节
      if (currentSection) {
        currentSection.content = currentSection.content.trimEnd();
        sections.push(currentSection);
      }
      // 开始新章节
      currentSection = {
        id: `section-${sections.length}`,
        title: h2Match[1]!.trim(),
        level: 2,
        content: "",
      };
    } else if (!foundFirstH2) {
      // 还没遇到第一个 ## ，收集到 preamble
      preambleLines.push(line);
    } else if (currentSection) {
      // 在章节内
      currentSection.content += line + "\n";
    }
  }

  // 保存最后一个章节
  if (currentSection) {
    currentSection.content = currentSection.content.trimEnd();
    sections.push(currentSection);
  }

  preamble = preambleLines.join("\n").trim();

  return { preamble, sections };
}

// ── 组件 ──────────────────────────────────────────

export interface CollapsibleReportProps {
  /** Markdown 格式的报告内容 */
  content: string;
  /** 是否启用打字动画 */
  animated?: boolean;
  /** 是否检查链接可信度 */
  checkLinkCredibility?: boolean;
  /** 额外 className */
  className?: string;
}

export function CollapsibleReport({
  content,
  animated = false,
  checkLinkCredibility = false,
  className,
}: CollapsibleReportProps) {
  const { preamble, sections } = useMemo(
    () => parseReportSections(content),
    [content],
  );

  // 如果没有章节结构，直接渲染原始 Markdown
  if (sections.length === 0) {
    return (
      <div className={cn(className)}>
        <Markdown animated={animated} checkLinkCredibility={checkLinkCredibility}>
          {content}
        </Markdown>
      </div>
    );
  }

  // 默认全部折叠
  const defaultOpen: string[] = [];

  return (
    <div className={cn(className)}>
      {/* 前言部分（## 之前的内容） */}
      {preamble && (
        <div className="mb-6">
          <Markdown animated={animated} checkLinkCredibility={checkLinkCredibility}>
            {preamble}
          </Markdown>
        </div>
      )}

      {/* 可折叠章节 */}
      <Accordion
        type="multiple"
        defaultValue={defaultOpen}
        className="w-full"
      >
        {sections.map((section) => (
          <AccordionItem
            key={section.id}
            value={section.id}
            className="border-b last:border-b-0"
          >
            <AccordionTrigger className="group py-3 text-left hover:no-underline">
              <div className="flex w-full items-center gap-2">
                <ChevronDown className="h-4 w-4 shrink-0 text-muted-foreground transition-transform duration-200 group-data-[state=open]:rotate-180" />
                <span className="text-sm font-semibold text-foreground">
                  {section.title}
                </span>
              </div>
            </AccordionTrigger>
            <AccordionContent className="pb-4 pt-0">
              <div className="pl-6">
                <Markdown
                  animated={false}
                  checkLinkCredibility={checkLinkCredibility}
                >
                  {section.content}
                </Markdown>
              </div>
            </AccordionContent>
          </AccordionItem>
        ))}
      </Accordion>
    </div>
  );
}
