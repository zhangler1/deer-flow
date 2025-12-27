// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

import { PythonOutlined } from "@ant-design/icons";
import { motion } from "framer-motion";
import { LRUCache } from "lru-cache";
import { BookOpenText, FileText, PencilRuler, Search } from "lucide-react";
import { useTranslations } from "next-intl";
import { useTheme } from "next-themes";
import { useMemo } from "react";
import SyntaxHighlighter from "react-syntax-highlighter";
import { docco } from "react-syntax-highlighter/dist/esm/styles/hljs";
import { dark } from "react-syntax-highlighter/dist/esm/styles/prism";

import { FavIcon } from "~/components/deer-flow/fav-icon";
import Image from "~/components/deer-flow/image";
import { LoadingAnimation } from "~/components/deer-flow/loading-animation";
import { Markdown } from "~/components/deer-flow/markdown";
import { RainbowText } from "~/components/deer-flow/rainbow-text";
import { Tooltip } from "~/components/deer-flow/tooltip";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "~/components/ui/accordion";
import { Skeleton } from "~/components/ui/skeleton";
import { findMCPTool } from "~/core/mcp";
import type { ToolCallRuntime } from "~/core/messages";
import { useMessage, useStore } from "~/core/store";
import { parseJSON } from "~/core/utils";
import { cn } from "~/lib/utils";
import { getToolDisplayText } from "~/lib/tool-translations";

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
  const ongoing = useStore((state) => state.ongoingResearchId === researchId);
  return (
    <>
      <ul className={cn("flex flex-col py-4", className)}>
        {activityIds.map(
          (activityId, i) =>
            i !== 0 && (
              <motion.li
                key={activityId}
                style={{ transition: "all 0.4s ease-out" }}
                initial={{ opacity: 0, y: 24 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{
                  duration: 0.4,
                  ease: "easeOut",
                }}
              >
                <ActivityMessage messageId={activityId} />
                <ActivityListItem messageId={activityId} />
                {i !== activityIds.length - 1 && <hr className="my-8" />}
              </motion.li>
            ),
        )}
      </ul>
      {ongoing && <LoadingAnimation className="mx-4 my-12" />}
    </>
  );
}

function ActivityMessage({ messageId }: { messageId: string }) {
  const message = useMessage(messageId);
  if (message?.agent && message.content) {
    if (message.agent !== "reporter" && message.agent !== "planner") {
      return (
        <div className="px-4 py-2">
          <Markdown animated checkLinkCredibility>
            {message.content}
          </Markdown>
        </div>
      );
    }
  }
  return null;
}

function ActivityListItem({ messageId }: { messageId: string }) {
  const message = useMessage(messageId);
  if (message) {
    if (!message.isStreaming && message.toolCalls?.length) {
      for (const toolCall of message.toolCalls) {
        if (toolCall.result?.startsWith("Error")) {
          return null;
        }
        if (toolCall.name === "web_search" || toolCall.name === "domain_fin_search") {
          return <WebSearchToolCall key={toolCall.id} toolCall={toolCall} />;
        } else if (toolCall.name === "crawl_tool") {
          return <CrawlToolCall key={toolCall.id} toolCall={toolCall} />;
        } else if (toolCall.name === "python_repl_tool") {
          return <PythonToolCall key={toolCall.id} toolCall={toolCall} />;
        } else if (toolCall.name === "local_search_tool") {
          return <RetrieverToolCall key={toolCall.id} toolCall={toolCall} />;
        } else {
          return <MCPToolCall key={toolCall.id} toolCall={toolCall} />;
        }
      }
    }
  }
  return null;
}

const __pageCache = new LRUCache<string, string>({ max: 100 });

// 统一的搜索结果类型（支持 web_search 和 domain_fin_search）
type SearchResult =
  | {
    type: "page";
    title: string;
    url: string;
    content: string;
    score?: number;      // 相关度评分（可选）
    source?: string;     // 来源（可选）
    category?: string;   // 分类（可选）
  }
  | {
    type: "image";
    image_url: string;
    image_description: string;
  };

function WebSearchToolCall({ toolCall }: { toolCall: ToolCallRuntime }) {
  const t = useTranslations("chat.research");
  const searching = useMemo(() => {
    return toolCall.result === undefined;
  }, [toolCall.result]);
  const searchResults = useMemo<SearchResult[]>(() => {
    let results: SearchResult[] | undefined = undefined;
    try {
      const parsed = toolCall.result ? parseJSON(toolCall.result, []) : undefined;
      if (Array.isArray(parsed)) {
        // 转换为统一格式，处理旧格式和新格式
        results = parsed.map((item: any) => {
          // 如果已经有 type 字段，直接使用
          if (item.type) {
            return item;
          }
          // 否则根据字段推断类型
          if (item.image_url) {
            return item; // 图片类型
          }
          // 默认为页面类型（支持统一后的格式）
          return {
            type: "page",
            title: item.title || "",
            url: item.url || "",
            content: item.content || "",
            score: item.score,
            source: item.source,
            category: item.category,
          };
        });
      } else {
        results = [];
      }
    } catch {
      results = undefined;
    }
    if (Array.isArray(results)) {
      results.forEach((result) => {
        if (result.type === "page") {
          __pageCache.set(result.url, result.title);
        }
      });
    } else {
      results = [];
    }
    return results;
  }, [toolCall.result]);
  const pageResults = useMemo(
    () => searchResults?.filter((result) => result.type === "page"),
    [searchResults],
  );
  const imageResults = useMemo(
    () => searchResults?.filter((result) => result.type === "image"),
    [searchResults],
  );
  return (
    <section className="mt-4 pl-4">
      <div className="font-medium italic">
        <RainbowText
          className="flex items-center"
          animated={searchResults === undefined}
        >
          <Search size={16} className={"mr-2"} />
          <span>{t("searchingFor")}&nbsp;</span>
          <span className="max-w-[500px] overflow-hidden text-ellipsis whitespace-nowrap">
            {(toolCall.args as { query: string }).query}
          </span>
        </RainbowText>
      </div>
      <div className="pr-4">
        {pageResults && (
          <ul className="mt-2 flex flex-wrap gap-4">
            {searching &&
              [...Array(3)].map((_, i) => (
                <li
                  key={`search-result-${i}`}
                  className="flex h-40 w-40 gap-2 rounded-md text-sm"
                >
                  <Skeleton
                    className="to-accent h-full w-full rounded-md bg-gradient-to-tl from-slate-400"
                    style={{ animationDelay: `${i * 0.2}s` }}
                  />
                </li>
              ))}
            {pageResults
              .filter((result) => result.type === "page")
              .slice(0, 3)
              .map((searchResult, i) => (
                <motion.li
                  key={`search-result-${i}`}
                  className="text-muted-foreground bg-accent flex max-w-xs flex-col gap-2 rounded-md px-3 py-2 text-sm"
                  initial={{ opacity: 0, y: 10, scale: 0.66 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  transition={{
                    duration: 0.2,
                    delay: i * 0.1,
                    ease: "easeOut",
                  }}
                >
                  <div className="flex items-start gap-2">
                    {/* 只有有URL时才显示FavIcon */}
                    {searchResult.url && (
                      <FavIcon
                        className="mt-1 shrink-0"
                        url={searchResult.url}
                        title={searchResult.title}
                      />
                    )}
                    {/* 如果有URL就显示为链接，否则显示为纯文本 */}
                    {searchResult.url ? (
                      <a 
                        href={searchResult.url} 
                        target="_blank"
                        className="flex-1 hover:underline line-clamp-2"
                      >
                        {searchResult.title}
                      </a>
                    ) : (
                      <span className="flex-1 line-clamp-2">
                        {searchResult.title}
                      </span>
                    )}
                  </div>
                  {/* 显示评分和来源信息 */}
                  {(searchResult.score !== undefined || searchResult.source) && (
                    <div className="flex items-center gap-2 text-xs text-muted-foreground/70">
                      {searchResult.score !== undefined && (
                        <span className="flex items-center gap-1">
                          <span className="text-yellow-500">⭐</span>
                          <span>{(searchResult.score * 100).toFixed(0)}%</span>
                        </span>
                      )}
                      {searchResult.source && (
                        <span className="flex items-center gap-1">
                          <span>📚</span>
                          <span>{searchResult.source}</span>
                        </span>
                      )}
                      {searchResult.category && (
                        <span className="flex items-center gap-1">
                          <span>🏷️</span>
                          <span>{searchResult.category}</span>
                        </span>
                      )}
                    </div>
                  )}
                </motion.li>
              ))}
            {imageResults.map((searchResult, i) => (
              <motion.li
                key={`search-result-${i}`}
                initial={{ opacity: 0, y: 10, scale: 0.66 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                transition={{
                  duration: 0.2,
                  delay: i * 0.1,
                  ease: "easeOut",
                }}
              >
                <a
                  className="flex flex-col gap-2 overflow-hidden rounded-md opacity-75 transition-opacity duration-300 hover:opacity-100"
                  href={searchResult.image_url}
                  target="_blank"
                >
                  <Image
                    src={searchResult.image_url}
                    alt={searchResult.image_description}
                    className="bg-accent h-40 w-40 max-w-full rounded-md bg-cover bg-center bg-no-repeat"
                    imageClassName="hover:scale-110"
                    imageTransition
                  />
                </a>
              </motion.li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}

function CrawlToolCall({ toolCall }: { toolCall: ToolCallRuntime }) {
  const t = useTranslations("chat.research");
  const url = useMemo(
    () => (toolCall.args as { url: string }).url,
    [toolCall.args],
  );
  const title = useMemo(() => __pageCache.get(url), [url]);
  
  // 解析爬虫结果，提取预览内容和摘要
  const crawlResult = useMemo(() => {
    if (!toolCall.result) return null;
    try {
      const result = JSON.parse(toolCall.result);
      // 如果标题是"未命名文档"，优先使用缓存中的标题
      const resultTitle = result.title === '未命名文档' || !result.title ? (title || result.url) : result.title;
      return {
        title: resultTitle,
        preview: result.preview,
        summary: result.summary,
        url: result.url,
      };
    } catch {
      return null;
    }
  }, [toolCall.result, title]);
  
  // 是否正在爬取
  const isCrawling = toolCall.result === undefined;
  
  return (
    <section className="mt-4 pl-4">
      <div>
        <RainbowText
          className="flex items-center text-base font-medium italic"
          animated={isCrawling}
        >
          <BookOpenText size={16} className={"mr-2"} />
          <span>{t("reading")}</span>
        </RainbowText>
      </div>
      <ul className="mt-2 flex flex-wrap gap-2">
        <motion.li
          className="text-muted-foreground bg-accent flex h-12 max-w-md gap-2 rounded-md px-2 py-1.5 text-sm items-center"
          initial={{ opacity: 0, y: 10, scale: 0.66 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          transition={{
            duration: 0.2,
            ease: "easeOut",
          }}
        >
          <FavIcon className="shrink-0" url={url} title={crawlResult?.title ?? title} />
          <a
            className="flex-grow overflow-hidden text-ellipsis whitespace-nowrap hover:underline"
            href={url}
            target="_blank"
          >
            {crawlResult?.title ?? title ?? url}
          </a>
        </motion.li>
      </ul>
      
      {/* 显示爬取内容预览 */}
      {crawlResult?.preview && (
        <motion.div
          className="mt-2 max-w-2xl rounded-md bg-accent/30 px-3 py-2 text-xs text-muted-foreground border border-accent"
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, ease: "easeOut" }}
        >
          <div className="line-clamp-3">
            {crawlResult.preview}
          </div>
        </motion.div>
      )}
      
      {/* 显示AI摘要（放在文章概括之后）*/}
      {crawlResult?.summary && (
        <motion.div
          className="mt-2 max-w-2xl rounded-md bg-blue-50 dark:bg-blue-950/30 px-3 py-2 text-sm border border-blue-200 dark:border-blue-800"
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, ease: "easeOut", delay: 0.1 }}
        >
          <div className="text-blue-900 dark:text-blue-100 leading-relaxed">
            {crawlResult.summary}
          </div>
        </motion.div>
      )}
    </section>
  );
}

function RetrieverToolCall({ toolCall }: { toolCall: ToolCallRuntime }) {
  const t = useTranslations("chat.research");
  const searching = useMemo(() => {
    return toolCall.result === undefined;
  }, [toolCall.result]);
  const documents = useMemo<
    Array<{ id: string; title: string; content: string }>
  >(() => {
    return toolCall.result ? parseJSON(toolCall.result, []) : [];
  }, [toolCall.result]);
  return (
    <section className="mt-4 pl-4">
      <div className="font-medium italic">
        <RainbowText className="flex items-center" animated={searching}>
          <Search size={16} className={"mr-2"} />
          <span>{t("retrievingDocuments")}&nbsp;</span>
          <span className="max-w-[500px] overflow-hidden text-ellipsis whitespace-nowrap">
            {(toolCall.args as { keywords: string }).keywords}
          </span>
        </RainbowText>
      </div>
      <div className="pr-4">
        {documents && (
          <ul className="mt-2 flex flex-wrap gap-4">
            {searching &&
              [...Array(2)].map((_, i) => (
                <li
                  key={`search-result-${i}`}
                  className="flex h-40 w-40 gap-2 rounded-md text-sm"
                >
                  <Skeleton
                    className="to-accent h-full w-full rounded-md bg-gradient-to-tl from-slate-400"
                    style={{ animationDelay: `${i * 0.2}s` }}
                  />
                </li>
              ))}
            {documents?.map((doc, i) => (
              <motion.li
                key={`search-result-${i}`}
                className="text-muted-foreground bg-accent flex max-w-40 gap-2 rounded-md px-2 py-1 text-sm"
                initial={{ opacity: 0, y: 10, scale: 0.66 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                transition={{
                  duration: 0.2,
                  delay: i * 0.1,
                  ease: "easeOut",
                }}
              >
                <FileText size={32} />
                {doc.title} (chunk-{i},size-{doc.content.length})
              </motion.li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}

function PythonToolCall({ toolCall }: { toolCall: ToolCallRuntime }) {
  const t = useTranslations("chat.research");
  const code = useMemo<string | undefined>(() => {
    return (toolCall.args as { code?: string }).code;
  }, [toolCall.args]);
  const { resolvedTheme } = useTheme();
  return (
    <section className="mt-4 pl-4">
      <div className="flex items-center">
        <PythonOutlined className={"mr-2"} />
        <RainbowText
          className="text-base font-medium italic"
          animated={toolCall.result === undefined}
        >
          {t("runningPythonCode")}
        </RainbowText>
      </div>
      <div>
        <div className="bg-accent mt-2 max-h-[400px] max-w-[calc(100%-120px)] overflow-y-auto rounded-md p-2 text-sm">
          <SyntaxHighlighter
            language="python"
            style={resolvedTheme === "dark" ? dark : docco}
            customStyle={{
              background: "transparent",
              border: "none",
              boxShadow: "none",
            }}
          >
            {code?.trim() ?? ""}
          </SyntaxHighlighter>
        </div>
      </div>
      {toolCall.result && <PythonToolCallResult result={toolCall.result} />}
    </section>
  );
}

function PythonToolCallResult({ result }: { result: string }) {
  const t = useTranslations("chat.research");
  const { resolvedTheme } = useTheme();
  const hasError = useMemo(
    () => result.includes("Error executing code:\n"),
    [result],
  );
  const error = useMemo(() => {
    if (hasError) {
      const parts = result.split("```\nError: ");
      if (parts.length > 1) {
        return parts[1]!.trim();
      }
    }
    return null;
  }, [result, hasError]);
  const stdout = useMemo(() => {
    if (!hasError) {
      const parts = result.split("```\nStdout: ");
      if (parts.length > 1) {
        return parts[1]!.trim();
      }
    }
    return null;
  }, [result, hasError]);
  return (
    <>
      <div className="mt-4 font-medium italic">
        {hasError ? t("errorExecutingCode") : t("executionOutput")}
      </div>
      <div className="bg-accent mt-2 max-h-[400px] max-w-[calc(100%-120px)] overflow-y-auto rounded-md p-2 text-sm">
        <SyntaxHighlighter
          language="plaintext"
          style={resolvedTheme === "dark" ? dark : docco}
          customStyle={{
            color: hasError ? "red" : "inherit",
            background: "transparent",
            border: "none",
            boxShadow: "none",
          }}
        >
          {error ?? stdout ?? "(empty)"}
        </SyntaxHighlighter>
      </div>
    </>
  );
}

function MCPToolCall({ toolCall }: { toolCall: ToolCallRuntime }) {
  const tool = useMemo(() => findMCPTool(toolCall.name), [toolCall.name]);
  const { resolvedTheme } = useTheme();
  return (
    <section className="mt-4 pl-4">
      <div className="w-fit overflow-y-auto rounded-md py-0 mcp-tool-container">
        <Accordion type="single" collapsible className="w-full">
          <AccordionItem value="item-1" className="border-0">
            <AccordionTrigger className="mcp-tool-accordion-trigger">
              <Tooltip title={tool?.description}>
                <div className="flex items-center font-medium italic">
                  <PencilRuler size={16} className={"mr-2"} />
                  <RainbowText
                    className="pr-0.5 text-base font-medium italic"
                    animated={toolCall.result === undefined}
                  >
                    正在运行 {toolCall.name ? getToolDisplayText(toolCall.name) : "MCP 工具"}
                  </RainbowText>
                </div>
              </Tooltip>
            </AccordionTrigger>
            <AccordionContent>
              {toolCall.result && (
                <div className="bg-accent max-h-[400px] max-w-[560px] overflow-y-auto rounded-md text-sm">
                  <SyntaxHighlighter
                    language="json"
                    style={resolvedTheme === "dark" ? dark : docco}
                    customStyle={{
                      background: "transparent",
                      border: "none",
                      boxShadow: "none",
                    }}
                  >
                    {toolCall.result.trim()}
                  </SyntaxHighlighter>
                </div>
              )}
            </AccordionContent>
          </AccordionItem>
        </Accordion>
      </div>
    </section>
  );
}

