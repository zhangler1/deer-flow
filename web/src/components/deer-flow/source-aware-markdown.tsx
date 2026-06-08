"use client";

import { useMemo } from "react";
import ReactMarkdown, {
  type Options as ReactMarkdownOptions,
} from "react-markdown";
import rehypeKatex from "rehype-katex";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import "katex/dist/katex.min.css";

import { rehypeSplitWordsIntoSpans } from "~/core/rehype";
import { type SourceDetail } from "~/core/source-store";
import { autoFixMarkdown } from "~/core/utils/markdown";
import { cn } from "~/lib/utils";

import Image from "./image";
import { Link } from "./link";
import { SourceTag } from "./source-tag";

// ── 类型 ──────────────────────────────────────────

export interface SourceAwareMarkdownProps {
  /** Markdown 内容 */
  children?: string | null;
  /** 额外 className */
  className?: string;
  /** 是否启用打字动画 */
  animated?: boolean;
  /** 是否检查链接可信度 */
  checkLinkCredibility?: boolean;
  /** 来源引用列表（用于 SourceTag tooltip 展示标题） */
  references?: SourceDetail[];
}

// ── 组件 ──────────────────────────────────────────

/**
 * 源感知 Markdown 渲染组件
 *
 * 在标准 Markdown 渲染基础上，检测 [(N)](URL) 格式的引用标记，
 * 将其渲染为可点击的 SourceTag 组件。
 *
 * Markdown 会将 [(N)](URL) 解析为一个 <a> 标签：
 * - href = URL
 * - children (文本) = "(N)"
 *
 * 本组件通过自定义 `a` component，判断文本是否匹配 /^\(\d+\)$/ 来识别溯源标记。
 */
export function SourceAwareMarkdown({
  children,
  className,
  animated = false,
  checkLinkCredibility = false,
  references,
}: SourceAwareMarkdownProps) {
  const components: ReactMarkdownOptions["components"] = useMemo(() => {
    return {
      a: ({ href, children: linkChildren }) => {
        // 检测 [(N)](URL) 模式：文本为 "(N)" 格式
        const text =
          typeof linkChildren === "string"
            ? linkChildren
            : Array.isArray(linkChildren)
              ? linkChildren.join("")
              : String(linkChildren ?? "");

        const sourceMatch = text.match(/^\((\d+)\)$/);

        if (sourceMatch && href) {
          const index = parseInt(sourceMatch[1]!, 10);
          return <SourceTag index={index} url={href} references={references} />;
        }

        // 非溯源标记：渲染为普通链接
        return (
          <Link href={href} checkLinkCredibility={checkLinkCredibility}>
            {linkChildren}
          </Link>
        );
      },
      img: ({ src, alt }) => (
        <a href={src as string} target="_blank" rel="noopener noreferrer">
          <Image className="rounded" src={src as string} alt={alt ?? ""} />
        </a>
      ),
    };
  }, [checkLinkCredibility, references]);

  const rehypePlugins = useMemo(() => {
    if (animated) {
      return [rehypeKatex, rehypeSplitWordsIntoSpans];
    }
    return [rehypeKatex];
  }, [animated]);

  return (
    <div className={cn(className, "prose dark:prose-invert max-w-full")}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm, remarkMath]}
        rehypePlugins={rehypePlugins}
        components={components}
      >
        {autoFixMarkdown(children ?? "")}
      </ReactMarkdown>
    </div>
  );
}
