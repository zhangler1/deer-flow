// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

import { LoadingOutlined } from "@ant-design/icons";
import { motion } from "framer-motion";
import {
  Download,
  Headphones,
  ChevronDown,
  ChevronRight,
  Lightbulb,
  Wrench,
  FileText,
} from "lucide-react";
import { useTranslations } from "next-intl";
import React, { useCallback, useMemo, useRef, useState, useImperativeHandle } from "react";

import { ClarificationCard } from "~/components/deer-flow/clarification-card";
import { LoadingAnimation } from "~/components/deer-flow/loading-animation";
import { FlowingText } from "~/components/deer-flow/flowing-text";
import { Markdown } from "~/components/deer-flow/markdown";
import { RainbowText } from "~/components/deer-flow/rainbow-text";
import { RollingText } from "~/components/deer-flow/rolling-text";
import {
  ScrollContainer,
  type ScrollContainerRef,
} from "~/components/deer-flow/scroll-container";
import { Tooltip } from "~/components/deer-flow/tooltip";
import { Button } from "~/components/ui/button";
import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
  CardTitle,
} from "~/components/ui/card";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "~/components/ui/collapsible";
import type { ClarificationQuestion, Message, Option } from "~/core/messages";
import {
  closeResearch,
  openResearch,
  useLastFeedbackMessageId,
  useLastInterruptMessage,
  useInterruptMessageFor,
  useMessageIds,
  useMessageSearchStatus,
  useMessageDisplayState,
  useResearchMessage,
  useStore,
  useAllIterationRounds,
} from "~/core/store";
import { parseJSON } from "~/core/utils";
import { cn } from "~/lib/utils";

import { ResearchTimer } from "./research-timer";

export function MessageListView({
  className,
  onFeedback,
  onSendMessage,
  onAtBottomChange,
  scrollRef,
  welcomeSlot,
  hideScrollbar,
}: {
  className?: string;
  onFeedback?: (feedback: { option: Option }) => void;
  onSendMessage?: (
    message: string,
    options?: { interruptFeedback?: string },
  ) => void;
  onAtBottomChange?: (atBottom: boolean) => void;
  scrollRef?: React.RefObject<ScrollContainerRef | null>;
  welcomeSlot?: React.ReactNode;
  hideScrollbar?: boolean;
}) {
  const scrollContainerRef = useRef<ScrollContainerRef>(null);
  // 将内部 scrollContainerRef 暂露给父级，用于外部滑动到底部按钮等场景
  useImperativeHandle(
    scrollRef,
    () => ({
      scrollToBottom: () => scrollContainerRef.current?.scrollToBottom(),
      forceScrollToBottom: () =>
        scrollContainerRef.current?.forceScrollToBottom(),
    }),
    [],
  );
  const messageIds = useMessageIds();
  const interruptMessage = useLastInterruptMessage();
  const waitingForFeedbackMessageId = useLastFeedbackMessageId();
  const responding = useStore((state) => state.responding);
  const noOngoingResearch = useStore(
    (state) => state.ongoingResearchId === null,
  );
  const ongoingResearchIsOpen = useStore(
    (state) => state.ongoingResearchId === state.openResearchId,
  );
  const researchIds = useStore((state) => state.researchIds);
  const messages = useStore((state) => state.messages);

  const handleToggleResearch = useCallback(() => {
    // Fix the issue where auto-scrolling to the bottom
    // occasionally fails when toggling research.
    const timer = setTimeout(() => {
      if (scrollContainerRef.current) {
        scrollContainerRef.current.scrollToBottom();
      }
    }, 500);
    return () => {
      clearTimeout(timer);
    };
  }, []);

  // 过滤出需要渲染的消息
  const visibleMessages = useMemo(() => {
    return messageIds
      .map((messageId) => {
        const message = messages.get(messageId);
        if (!message) return null;
        
        const startOfResearch = researchIds.includes(messageId);
        
        // 检查是否应该渲染这个消息
        // 用户消息、coordinator、planner、podcast、深度研究节点、智能路由节点、问题澄清卡片都应该显示
        if (!(
          message.role === "user" ||
          message.agent === "coordinator" ||
          message.agent === "planner" ||
          message.agent === "podcast" ||
          message.agent === "router" ||
          message.agent === "direct_answer_node" ||
          message.agent === "simple_search_node" ||
          message.agent === "iterative_research_node" ||  // 添加迭代研究节点消息显示
          message.agent === "iterative_reporter_node" ||
          message.agent === "system" ||  // 终止提示等系统消息
          message.tag === "clarification" ||  // 问题澄清卡片始终显示
          startOfResearch
        )) {
          return null;
        }        
        return {
          messageId,
          message,
          startOfResearch,
        };
      })
      .filter((item): item is { messageId: string; message: Message; startOfResearch: boolean } => item !== null);
  }, [messageIds, messages, researchIds]);

  // 获取所有轮次信息
  const allRounds = useAllIterationRounds();
  
  // 按轮次组织迭代研究消息
  const organizedMessages = useMemo(() => {
    // 鉴别联合类型：TS 可以根据 type 自动收窄、避免逐个打 `!`
    type OrganizedItem =
      | { type: 'round'; iteration: number; messageIds: string[]; collapsed: boolean }
      | { type: 'normal'; messageId: string; message: Message; startOfResearch: boolean };
    const result: OrganizedItem[] = [];
    
    // 创建一个set来跟踪已经在轮次中的消息
    const messagesInRounds = new Set<string>();
    
    // 收集所有轮次中的消息
    allRounds.forEach(round => {
      round.messageIds.forEach(id => messagesInRounds.add(id));
    });
    
    // 构建消息索引映射
    const messageIndexMap = new Map<string, number>();
    messageIds.forEach((id, index) => {
      messageIndexMap.set(id, index);
    });
    
    // 遍历所有可见消息，按照原始顺序处理
    visibleMessages.forEach(item => {
      // 如果消息在某个轮次中，检查是否需要插入该轮次容器
      const messageRound = allRounds.find(r => r.messageIds.includes(item.messageId));
      
      if (messageRound) {
        // 检查该轮次容器是否已经添加
        const alreadyAdded = result.some(r => r.type === 'round' && r.iteration === messageRound.iteration);

        if (!alreadyAdded) {
          // 第一次遇到该轮次的消息，添加轮次容器
          result.push({
            type: 'round',
            iteration: messageRound.iteration,
            messageIds: messageRound.messageIds,
            collapsed: messageRound.collapsed,
          });
        }
      } else {
        // 不在轮次中的普通消息，直接添加
        result.push({
          type: 'normal',
          messageId: item.messageId,
          message: item.message,
          startOfResearch: item.startOfResearch,
        });
      }
    });
    
    return result;
  }, [visibleMessages, allRounds, messageIds]);

  return (
    <ScrollContainer
      className={cn("flex h-full w-full flex-col overflow-hidden", className)}
      scrollShadow={false}
      autoScrollToBottom={!welcomeSlot}
      onAtBottomChange={onAtBottomChange}
      hideScrollbar={hideScrollbar}
      ref={scrollContainerRef}
    >
      {/* 空状态：展示欢迎语和 FeatureShowcase */}
      {welcomeSlot && organizedMessages.length === 0 && (
        <div className="flex flex-col items-center flex-1 px-4 pt-6 pb-4 w-full max-w-[1000px] mx-auto">
          {welcomeSlot}
        </div>
      )}
      <ul className="flex flex-col w-full max-w-[768px] mx-auto">
        {organizedMessages.map((item, _index) => {
          if (item.type === 'round') {
            // 渲染轮次容器
            return (
              <IterativeResearchRoundContainer
                key={`round_${item.iteration}`}
                iteration={item.iteration}
                messageIds={item.messageIds}
                collapsed={item.collapsed}
                _onFeedback={onFeedback}
                _onSendMessage={onSendMessage}
              />
            );
          } else {
            // 渲染普通消息
            return (
              <MessageListItem
                key={item.messageId}
                messageId={item.messageId}
                message={item.message}
                startOfResearch={item.startOfResearch}
                waitForFeedback={waitingForFeedbackMessageId === item.messageId}
                interruptMessage={interruptMessage}
                onFeedback={onFeedback}
                onSendMessage={onSendMessage}
                onToggleResearch={handleToggleResearch}
              />
            );
          }
        })}
        <div className="flex h-8 w-full shrink-0"></div>
      </ul>
      {/* 问题澄清卡片渲染已移至 MessageListItem 内联，确保历史消息中卡片不消失 */}
      {responding && (noOngoingResearch || !ongoingResearchIsOpen) && (
        <LoadingAnimation className="ml-4 mb-4 w-full max-w-[768px] mx-auto" />
      )}
    </ScrollContainer>
  );
}

function MessageBubble({
  className,
  message,
  children,
}: {
  className?: string;
  message: Message;
  children: React.ReactNode;
}) {
  return (
    <div
      className={cn(
        "group flex w-auto max-w-[90vw] flex-col rounded-2xl px-4 py-3 break-words",
        message.role === "user" && "bg-brand rounded-ee-none",
        message.role === "assistant" && "bg-card rounded-es-none",
        className,
      )}
      style={{ wordBreak: "break-all" }}
    >
      {children}
    </div>
  );
}

function IterativeResearchRoundContainer({
  iteration,
  messageIds,
  collapsed,
  _onFeedback,
  _onSendMessage,
}: {
  iteration: number;
  messageIds: string[];
  collapsed: boolean;
  _onFeedback?: (feedback: { option: Option }) => void;
  _onSendMessage?: (
    message: string,
    options?: { interruptFeedback?: string },
  ) => void;
}) {
  const [isOpen, setIsOpen] = useState(!collapsed);
  const messages = useStore((state) => state.messages);
  
  // 监听collapsed状态变化，自动折叠
  React.useEffect(() => {
    if (collapsed) {
      setIsOpen(false);
    }
  }, [collapsed]);
  
  // 检查是否有消息还在流式传输
  const hasStreaming = useMemo(() => {
    return messageIds.some(id => {
      const msg = messages.get(id);
      return msg?.isStreaming;
    });
  }, [messageIds, messages]);
  
  return (
    <motion.li
      className="mt-4"
      initial={{ opacity: 0, y: 24 }}
      animate={{ opacity: 1, y: 0 }}
      style={{ transition: "all 0.2s ease-out" }}
      transition={{
        duration: 0.2,
        ease: "easeOut",
      }}
    >
      <div className="w-full px-4">
        <Collapsible open={isOpen} onOpenChange={setIsOpen}>
          <CollapsibleTrigger asChild>
            <Button
              variant="ghost"
              className={cn(
                "h-auto w-full justify-start rounded-xl border px-6 py-4 text-left transition-all duration-200 mb-3",
                "hover:bg-accent hover:text-accent-foreground",
                hasStreaming
                  ? "border-[#cce0ff] bg-[#e8f0fe] shadow-md dark:border-[#1a4060] dark:bg-[#102030]"
                  : "border-border bg-card/50",
              )}
            >
              <div className="flex w-full items-center gap-3">
                <span
                  className={cn(
                    "text-lg leading-none font-bold transition-colors duration-200",
                    hasStreaming ? "text-primary" : "text-foreground",
                  )}
                >
                  第{iteration}轮研究
                </span>
                {hasStreaming && <LoadingAnimation className="ml-2 scale-75" />}
                <div className="flex-grow" />
                {isOpen ? (
                  <ChevronDown
                    size={18}
                    className="text-muted-foreground transition-transform duration-200"
                  />
                ) : (
                  <ChevronRight
                    size={18}
                    className="text-muted-foreground transition-transform duration-200"
                  />
                )}
              </div>
            </Button>
          </CollapsibleTrigger>
          <CollapsibleContent className="data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 data-[state=closed]:slide-up-2 data-[state=open]:slide-down-2">
            <div className="flex flex-col gap-3">
              {messageIds.map((messageId) => {
                const message = messages.get(messageId);
                if (!message) return null;
                return (
                  <IterativeResearchCard key={messageId} message={message} />
                );
              })}
            </div>
          </CollapsibleContent>
        </Collapsible>
      </div>
    </motion.li>
  );
}

function IterativeResearchCard({ message }: { message: Message }) {
  const t = useTranslations("chat.research");
  const [isOpen, setIsOpen] = useState(true);
  const [hasAutoCollapsed, setHasAutoCollapsed] = useState(false);
  
  // 从全局 store 中获取消息的显示状态（用于恢复折叠框状态）
  const displayState = useMessageDisplayState(message.id);
  
  // 使用专门的选择器获取当前消息的搜索状态，确保每个卡片独立
  const messageSearchStatus = useMessageSearchStatus(message.id);
  // 监听消息列表的变化
  const messageIds = useMessageIds();
  const currentMessageIndex = messageIds.indexOf(message.id);

  // 监听 tag 变化，一旦出现 round_progress 就记录到 store（最高优先级）
  React.useEffect(() => {
    if (message.tag === "round_progress" && !displayState.hasShownRoundProgress) {
      useStore.getState().updateMessageDisplayState(message.id, {
        hasShownRoundProgress: true,
        preservedRoundText: message.roundText,
      });
    }
  }, [message.tag, message.roundText, message.id, displayState.hasShownRoundProgress]);

  // 监听 tag 变化，一旦出现 searching 就记录到 store
  React.useEffect(() => {
    if (message.tag === "searching" && !displayState.hasShownSearching) {
      useStore.getState().updateMessageDisplayState(message.id, {
        hasShownSearching: true,
      });
    }
  }, [message.tag, message.id, displayState.hasShownSearching]);
  
  // 监听 tag 变化，一旦出现 crawling 就记录到 store
  React.useEffect(() => {
    if (message.tag === "crawling" && !displayState.hasShownCrawling) {
      useStore.getState().updateMessageDisplayState(message.id, {
        hasShownCrawling: true,
      });
    }
  }, [message.tag, message.id, displayState.hasShownCrawling]);

  // 当消息完成流式传输时自动折叠
  React.useEffect(() => {
    if (!message.isStreaming && !hasAutoCollapsed) {
      setIsOpen(false);
      setHasAutoCollapsed(true);
    }
  }, [message.isStreaming, hasAutoCollapsed]);

  // 当有新消息出现时，自动折叠未完成的迭代研究对话框
  React.useEffect(() => {
    // 检查是否有后续消息
    if (currentMessageIndex !== -1 && currentMessageIndex < messageIds.length - 1) {
      // 如果当前消息还在流式传输中，则折叠它
      if (message.isStreaming && !hasAutoCollapsed) {
        setIsOpen(false);
        setHasAutoCollapsed(true);
      }
    }
  }, [messageIds.length, currentMessageIndex, message.isStreaming, hasAutoCollapsed]);

  // 查找所有搜索工具调用
  const allSearchTools = useMemo(() => {
    if (!message.toolCalls) return [];
    // 查找所有搜索工具（web_search）
    return message.toolCalls.filter(
      (toolCall) => toolCall.name === "web_search"
    );
  }, [message.toolCalls]);
  
  // 查找所有爬虫工具调用
  const allCrawlTools = useMemo(() => {
    if (!message.toolCalls) return [];
    // 查找所有爬虫工具（crawl_tool）
    return message.toolCalls.filter(
      (toolCall) => toolCall.name === "crawl_tool"
    );
  }, [message.toolCalls]);
  
  // 从所有已完成的搜索工具中提取完整的搜索关键字
  const completedSearchKeywords = useMemo(() => {
    if (allSearchTools.length === 0) return [];
    
    const keywords: string[] = [];
    
    allSearchTools.forEach((toolCall) => {
      // 只处理已经完成的工具调用（有result或argsChunks已完整）
      if (!toolCall.args?.query) return;
      
      const query = toolCall.args.query as string;
      if (query && !keywords.includes(query)) {
        keywords.push(query);
      }
    });
    
    return keywords;
  }, [allSearchTools]);
  
  // 从所有已完成的爬虫工具中提取完整的URL
  const completedCrawlUrls = useMemo(() => {
    if (allCrawlTools.length === 0) return [];
    
    const urls: string[] = [];
    
    allCrawlTools.forEach((toolCall) => {
      // 只处理已经完成的工具调用
      if (!toolCall.args?.url) return;
      
      const url = toolCall.args.url as string;
      if (url && !urls.includes(url)) {
        urls.push(url);
      }
    });
    
    return urls;
  }, [allCrawlTools]);
  
  // 获取当前正在流式传输的搜索关键词（用于实时显示）
  const currentStreamingKeywords = useMemo(() => {
    if (!message.isStreaming || allSearchTools.length === 0) return [];
    
    const keywords: string[] = [];
    
    allSearchTools.forEach((toolCall) => {
      // 只处理正在流式传输的工具调用（有argsChunks但可能还没result）
      if (!toolCall.argsChunks || toolCall.argsChunks.length === 0) return;
      
      try {
        // 尝试解析已有的 args chunks 为 JSON
        const argsString = toolCall.argsChunks.join("");
        // 使用正则提取 query 字段的值（可能是不完整的JSON）
        const queryMatch = /"query"\s*:\s*"([^"]*)"/.exec(argsString);
        if (queryMatch?.[1] && !keywords.includes(queryMatch[1])) {
          keywords.push(queryMatch[1]);
        }
      } catch {
        // 忽略解析错误
      }
    });
    
    return keywords;
  }, [allSearchTools, message.isStreaming]);
  
  // 获取当前正在流式传输的爬虫URL（用于实时显示）
  const currentStreamingUrls = useMemo(() => {
    if (!message.isStreaming || allCrawlTools.length === 0) return [];
    
    const urls: string[] = [];
    
    allCrawlTools.forEach((toolCall) => {
      // 只处理正在流式传输的工具调用
      if (!toolCall.argsChunks || toolCall.argsChunks.length === 0) return;
      
      try {
        const argsString = toolCall.argsChunks.join("");
        // 使用正则提取 url 字段的值
        const urlMatch = /"url"\s*:\s*"([^"]*)"/.exec(argsString);
        if (urlMatch?.[1] && !urls.includes(urlMatch[1])) {
          urls.push(urlMatch[1]);
        }
      } catch {
        // 忽略解析错误
      }
    });
    
    return urls;
  }, [allCrawlTools, message.isStreaming]);
  
  // 保留已完成的搜索关键词到 store
  React.useEffect(() => {
    if (completedSearchKeywords.length > 0) {
      useStore.getState().updateMessageDisplayState(message.id, {
        preservedSearchKeywords: completedSearchKeywords,
      });
    }
  }, [completedSearchKeywords, message.id]);
    
  // 保留已完成的爬虯URL到 store
  React.useEffect(() => {
    if (completedCrawlUrls.length > 0) {
      useStore.getState().updateMessageDisplayState(message.id, {
        preservedCrawlUrls: completedCrawlUrls,
      });
    }
  }, [completedCrawlUrls, message.id]);

  // 确定显示的文本 - 优先级：round_progress > crawling > searching > 其他状态
  const displayText = useMemo(() => {
    // 最高优先级：如果曾经显示过 round_progress（第X轮研究进展），固定显示该状态
    if (displayState.hasShownRoundProgress) {
      return displayState.preservedRoundText ?? t("iterativeResearchProcess");
    }

    // 第二优先级：如果曾经显示过 crawling，一直保持显示 crawling（crawling 优先级高于 searching）
    if (displayState.hasShownCrawling) {
      return t("crawling");
    }

    // 第三优先级：如果曾经显示过 searching，一直保持显示 searching
    if (displayState.hasShownSearching) {
      return t("searching");
    }

    // 优先使用 message.tag
    if (message.tag && message.isStreaming) {
      switch (message.tag) {
        case "routing":
          return t("routing");
        case "planning":
          return t("planning");
        case "searching":
          return t("searching");
        case "crawling":
          return t("crawling");
        case "iterative_answering":
          return t("iterativeAnswering");
        case "reporting":
          return t("reporting");
        case "waiting_for_feedback":
          return t("waitingForFeedback");
        case "clarification":
          return "正在澄清问题";
        case "error":
          return t("error");
        case "answering":
          return t("answering");
        case "round_progress":
          return message.roundText ?? t("iterativeResearchProcess"); // 显示"第X轮研究进展"
        default:
          break;
      }
    }
    
    // 降级：检查当前消息是否正在进行搜索（从 messageSearchStatus）
    if (messageSearchStatus && message.isStreaming) {
      return t("searching"); // "正在搜索"
    }
    
    // 默认显示"正在研究"
    return t("iterativeResearchProcess"); // "正在研究"
  }, [displayState.hasShownRoundProgress, displayState.preservedRoundText, displayState.hasShownCrawling, displayState.hasShownSearching, message.tag, message.roundText, messageSearchStatus, message.isStreaming, t]);
  
  return (
    <div className="w-full">
      <Collapsible open={isOpen} onOpenChange={setIsOpen}>
        <CollapsibleTrigger asChild>
          <Button
            variant="ghost"
            className={cn(
              "h-auto w-full justify-start rounded-xl border px-6 py-4 text-left transition-all duration-200",
              "hover:bg-accent hover:text-accent-foreground",
              message.isStreaming
                ? "border-[#cce0ff] bg-[#f0f4fd] shadow-sm dark:border-[#1a4060] dark:bg-[#0e1825]"
                : "border-border bg-card",
            )}
          >
            <div className="flex w-full items-center gap-3">
              <Lightbulb
                size={18}
                className={cn(
                  "shrink-0 transition-colors duration-200",
                  message.isStreaming ? "text-primary" : "text-muted-foreground",
                )}
              />
              <span
                className={cn(
                  "leading-none font-semibold transition-colors duration-200",
                  message.isStreaming ? "text-primary" : "text-foreground",
                )}
              >
                {displayText}
              </span>
              {/* 显示搜索关键词 */}
              {(currentStreamingKeywords.length > 0 || displayState.preservedSearchKeywords.length > 0) && (
                <span
                  className={cn(
                    "ml-2 max-w-[500px] overflow-hidden text-ellipsis whitespace-nowrap text-sm font-normal transition-colors duration-200",
                    message.isStreaming ? "text-primary/80" : "text-muted-foreground",
                  )}
                >
                  : {(currentStreamingKeywords.length > 0 ? currentStreamingKeywords : displayState.preservedSearchKeywords).join(" | ")}
                </span>
              )}
              {/* 显示爬虯URL */}
              {(currentStreamingUrls.length > 0 || displayState.preservedCrawlUrls.length > 0) && (
                <span
                  className={cn(
                    "ml-2 max-w-[500px] overflow-hidden text-ellipsis whitespace-nowrap text-sm font-normal transition-colors duration-200",
                    message.isStreaming ? "text-primary/80" : "text-muted-foreground",
                  )}
                >
                  : {(currentStreamingUrls.length > 0 ? currentStreamingUrls : displayState.preservedCrawlUrls).join(" | ")}
                </span>
              )}
              {message.isStreaming && <LoadingAnimation className="ml-2 scale-75" />}
              <div className="flex-grow" />
              {isOpen ? (
                <ChevronDown
                  size={16}
                  className="text-muted-foreground transition-transform duration-200"
                />
              ) : (
                <ChevronRight
                  size={16}
                  className="text-muted-foreground transition-transform duration-200"
                />
              )}
            </div>
          </Button>
        </CollapsibleTrigger>
        <CollapsibleContent className="data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 data-[state=closed]:slide-up-2 data-[state=open]:slide-down-2 mt-3">
          <Card
            className={cn(
              "transition-all duration-200",
              message.isStreaming ? "border-[#cce0ff] bg-[#f0f4fd] dark:border-[#1a4060] dark:bg-[#0e1825]" : "border-border",
            )}
          >
            <CardContent>
              <div className="flex h-40 w-full overflow-y-auto">
                <ScrollContainer
                  className="flex h-full w-full flex-col overflow-hidden"
                  scrollShadow={false}
                  autoScrollToBottom={message.isStreaming}
                >
                  <Markdown
                    className={cn(
                      "prose dark:prose-invert max-w-none transition-colors duration-200",
                      message.isStreaming ? "prose-primary" : "opacity-80",
                    )}
                    animated={message.isStreaming}
                  >
                    {message.content}
                  </Markdown>
                </ScrollContainer>
              </div>
            </CardContent>
          </Card>
        </CollapsibleContent>
      </Collapsible>
    </div>
  );
}

function MessageListItem({
  className,
  messageId,
  message,
  startOfResearch,
  waitForFeedback,
  interruptMessage: _interruptMessage,
  onFeedback,
  onSendMessage,
  onToggleResearch,
}: {
  className?: string;
  messageId: string;
  message: Message;
  startOfResearch: boolean;
  waitForFeedback?: boolean;
  onFeedback?: (feedback: { option: Option }) => void;
  interruptMessage?: Message | null;
  onSendMessage?: (
    message: string,
    options?: { interruptFeedback?: string },
  ) => void;
  onToggleResearch?: () => void;
}) {
  // 为计划消息获取正确的中断消息
  const specificInterruptMessage = useInterruptMessageFor(messageId);

  let content: React.ReactNode;
  
  if (message.agent === "planner") {
    content = (
      <div className="w-full px-4">
        <PlanCard
          message={message}
          waitForFeedback={waitForFeedback}
          interruptMessage={specificInterruptMessage}
          onFeedback={onFeedback}
          onSendMessage={onSendMessage}
        />
      </div>
    );
  } else if (message.agent === "podcast") {
    content = (
      <div className="w-full px-4">
        <PodcastCard message={message} />
      </div>
    );
  } else if (startOfResearch) {
    content = (
      <StartOfResearchBlock
        researchId={message.id}
        onToggleResearch={onToggleResearch}
      />
    );
  } else if (message.agent === "iterative_research_node") {
    // 特殊处理迭代研究节点的消息
    content = (
      <div className="w-full px-4">
        <IterativeResearchCard message={message} />
      </div>
    );
  } else if (message.tag === "clarification" && message.clarificationQuestions?.length) {
    // 问题澄清卡片：内联渲染，确保提交后卡片不消失
    // 判断是否仍处于可交互状态：当前活跃的 interrupt 消息才是可操作的
    const isLive = _interruptMessage?.id === message.id;
    content = (
      <div className="w-full px-4">
        <ClarificationCardWrapper
          questions={message.clarificationQuestions}
          onSendMessage={onSendMessage}
          alreadySubmitted={!isLive}
        />
      </div>
    );
  } else {
    content = message.content ? (
      <div
        className={cn(
          "flex w-full px-4",
          message.role === "user" && "justify-end",
          className,
        )}
      >
        <MessageBubble message={message}>
          <div className="flex w-full flex-col break-words">
            <Markdown
              className={cn(
                message.role === "user" &&
                  "prose-invert not-dark:text-secondary dark:text-inherit",
              )}
            >
              {message?.content}
            </Markdown>
          </div>
        </MessageBubble>
      </div>
    ) : null;
  }
  
  // 如果没有内容，不渲染任何东西
  if (!content) {
    return null;
  }
  
  return (
    <motion.li
      className="mt-4"
      key={messageId}
      initial={{ opacity: 0, y: 24 }}
      animate={{ opacity: 1, y: 0 }}
      style={{ transition: "all 0.2s ease-out" }}
      transition={{
        duration: 0.2,
        ease: "easeOut",
      }}
    >
      {content}
    </motion.li>
  );
}

function StartOfResearchBlock({
  researchId,
  onToggleResearch,
}: {
  researchId: string;
  onToggleResearch?: () => void;
}) {
  // 跟随内部 ResearchCard 的逻辑：当该 research 已有 report 且 report 不再流式传输，则视为生成完成
  const reportId = useStore((state) => state.researchReportIds.get(researchId));
  const reportGenerated = useStore((state) => {
    if (!reportId) return false;
    const msg = state.messages.get(reportId);
    return !!msg && !msg.isStreaming;
  });
  // 研究是否还在进行中（被取消或正常结束后都应停止动画）
  const researchOngoing = useStore(
    (state) => state.ongoingResearchId === researchId,
  );
  // 只有「研究还在进行」且「报告未完成」时才流动，否则停止动画
  const flowingAnimated = researchOngoing && !reportGenerated;
  return (
    <div className="px-4 flex flex-col gap-2">
      <div className="text-base font-medium text-foreground w-fit max-w-full">
        <FlowingText animated={flowingAnimated}>
          接下来将为你生成报告：
        </FlowingText>
      </div>
      <ResearchCard
        className="w-[340px] max-w-full"
        researchId={researchId}
        onToggleResearch={onToggleResearch}
      />
    </div>
  );
}

function ResearchCard({
  className,
  researchId,
  onToggleResearch,
}: {
  className?: string;
  researchId: string;
  onToggleResearch?: () => void;
}) {
  const t = useTranslations("chat.research");
  const reportId = useStore((state) => state.researchReportIds.get(researchId));
  const hasReport = reportId !== undefined;
  const reportGenerating = useStore(
    (state) => hasReport && state.messages.get(reportId)!.isStreaming,
  );
  const openResearchId = useStore((state) => state.openResearchId);
  const state = useMemo(() => {
    if (hasReport) {
      return reportGenerating ? t("generatingReport") : t("reportGenerated");
    }
    return t("researching");
  }, [hasReport, reportGenerating, t]);
  const msg = useResearchMessage(researchId);
  const title = useMemo(() => {
    if (msg) {
      return parseJSON(msg.content ?? "", { title: "" }).title;
    }
    return undefined;
  }, [msg]);
  const handleOpen = useCallback(() => {
    if (openResearchId === researchId) {
      closeResearch();
    } else {
      openResearch(researchId);
    }
    onToggleResearch?.();
  }, [openResearchId, researchId, onToggleResearch]);
  const isOpen = openResearchId === researchId;
  // 研究是否正在进行中（用于判断是否显示进度条）
  const researchOngoing = useStore(
    (s) => s.ongoingResearchId === researchId,
  );
  // 里程碑数据（完成后仍保留，用于显示历史记录）
  const hasMilestones = useStore(
    (s) => s.researchMilestones.length > 0 || s.reporterCompletedAt !== null,
  );
  return (
    <Card
      className={cn(
        "w-full cursor-pointer transition-all duration-200 hover:shadow-md hover:border-gray-300",
        isOpen
          ? "bg-[linear-gradient(109deg,rgb(243,247,255)_0%,white_50%,white_100%)] !bg-transparent ring-1 ring-primary/20 border-primary/30"
          : "bg-[linear-gradient(to_right,white_0%,white_50%,rgb(243,247,255)_100%)]",
        className,
      )}
      onClick={handleOpen}
    >
      <div className="flex items-center py-1.5 px-2 gap-2">
        {/* 左侧图标 */}
        <div className="shrink-0 flex items-center justify-center w-6 h-6 rounded bg-primary/10 text-primary">
          <FileText className="w-3.5 h-3.5" />
        </div>
        {/* 中间信息 */}
        <div className="flex-1 min-w-0">
          <div className="font-medium text-sm text-foreground truncate">
            {title !== undefined && title !== "" ? title : t("deepResearch")}
          </div>
          <RollingText className="text-muted-foreground text-xs">
            {state}
          </RollingText>
        </div>
      </div>
      {/* 进度条：研究进行中 或 有已完成的里程碑 时显示 */}
      {(researchOngoing || hasMilestones) && (
        <ResearchTimer compact className="border-t border-primary/10" />
      )}
    </Card>
  );
}

/** 历史报告卡片（继续对话时显示在消息列表顶部） */
export function HistoricalReportCard({
  className,
}: {
  className?: string;
}) {
  const ctx = useStore((s) => s.continuingReportContext);
  const openReportViewer = useStore((s) => s.openReportViewer);
  const handleClick = useCallback(() => {
    if (ctx) {
      openReportViewer(ctx.reportId, ctx.content, ctx.title);
    }
  }, [ctx, openReportViewer]);

  if (!ctx) return null;

  return (
    <Card
      className={cn(
        "w-full cursor-pointer transition-all duration-200 hover:shadow-md hover:border-gray-300",
        "bg-[linear-gradient(to_right,white_0%,white_50%,rgb(243,247,255)_100%)]",
        className,
      )}
      onClick={handleClick}
    >
      <div className="flex items-center py-1.5 px-2 gap-2">
        {/* 左侧图标 */}
        <div className="shrink-0 flex items-center justify-center w-6 h-6 rounded bg-primary/10 text-primary">
          <FileText className="w-3.5 h-3.5" />
        </div>
        {/* 中间信息 */}
        <div className="flex-1 min-w-0">
          <div className="font-medium text-sm text-foreground truncate">
            {ctx.title || "历史报告"}
          </div>
          <span className="text-muted-foreground text-xs">
            历史报告 · 点击回看
          </span>
        </div>
      </div>
    </Card>
  );
}

function ThoughtBlock({
  className,
  content,
  isStreaming,
  hasMainContent,
}: {
  className?: string;
  content: string;
  isStreaming?: boolean;
  hasMainContent?: boolean;
}) {
  const t = useTranslations("chat.research");
  const [isOpen, setIsOpen] = useState(true);

  const [hasAutoCollapsed, setHasAutoCollapsed] = useState(false);

  React.useEffect(() => {
    if (hasMainContent && !hasAutoCollapsed) {
      setIsOpen(false);
      setHasAutoCollapsed(true);
    }
  }, [hasMainContent, hasAutoCollapsed]);

  if (!content || content.trim() === "") {
    return null;
  }

  return (
    <div className={cn("mb-6 w-full", className)}>
      <Collapsible open={isOpen} onOpenChange={setIsOpen}>
        <CollapsibleTrigger asChild>
          <Button
            variant="ghost"
            className={cn(
              "h-auto w-full justify-start rounded-xl border px-6 py-4 text-left transition-all duration-200",
              "hover:bg-accent hover:text-accent-foreground",
              isStreaming
                ? "border-[#cce0ff] bg-[#f0f4fd] shadow-sm dark:border-[#1a4060] dark:bg-[#0e1825]"
                : "border-border bg-card",
            )}
          >
            <div className="flex w-full items-center gap-3">
              <Lightbulb
                size={18}
                className={cn(
                  "shrink-0 transition-colors duration-200",
                  isStreaming ? "text-primary" : "text-muted-foreground",
                )}
              />
              <span
                className={cn(
                  "leading-none font-semibold transition-colors duration-200",
                  isStreaming ? "text-primary" : "text-foreground",
                )}
              >
                {t("deepThinking")}
              </span>
              {isStreaming && <LoadingAnimation className="ml-2 scale-75" />}
              <div className="flex-grow" />
              {isOpen ? (
                <ChevronDown
                  size={16}
                  className="text-muted-foreground transition-transform duration-200"
                />
              ) : (
                <ChevronRight
                  size={16}
                  className="text-muted-foreground transition-transform duration-200"
                />
              )}
            </div>
          </Button>
        </CollapsibleTrigger>
        <CollapsibleContent className="data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 data-[state=closed]:slide-up-2 data-[state=open]:slide-down-2 mt-3">
          <Card
            className={cn(
              "transition-all duration-200",
              isStreaming ? "border-[#cce0ff] bg-[#f0f4fd] dark:border-[#1a4060] dark:bg-[#0e1825]" : "border-border",
            )}
          >
            <CardContent>
              <div className="flex h-40 w-full overflow-y-auto">
                <ScrollContainer
                  className={cn(
                    "flex h-full w-full flex-col overflow-hidden",
                    className,
                  )}
                  scrollShadow={false}
                  autoScrollToBottom
                >
                  <Markdown
                    className={cn(
                      "prose dark:prose-invert max-w-none transition-colors duration-200",
                      isStreaming ? "prose-primary" : "opacity-80",
                    )}
                    animated={isStreaming}
                  >
                    {content}
                  </Markdown>
                </ScrollContainer>
              </div>
            </CardContent>
          </Card>
        </CollapsibleContent>
      </Collapsible>
    </div>
  );
}

const GREETINGS = ["好的", "太棒了", "看起来不错", "很好", "完美"];
function PlanCard({
  className,
  message,
  interruptMessage,
  onFeedback,
  waitForFeedback,
  onSendMessage,
}: {
  className?: string;
  message: Message;
  interruptMessage?: Message | null;
  onFeedback?: (feedback: { option: Option }) => void;
  onSendMessage?: (
    message: string,
    options?: { interruptFeedback?: string },
  ) => void;
  waitForFeedback?: boolean;
}) {
  const t = useTranslations("chat.research");
  const plan = useMemo<{
    title?: string;
    thought?: string;
    steps?: { title?: string; description?: string; tools?: string[] }[];
  }>(() => {
    return parseJSON(message.content ?? "", {});
  }, [message.content]);

  const reasoningContent = message.reasoningContent;
  const hasMainContent = Boolean(
    message.content && message.content.trim() !== "",
  );

  // 判断是否正在思考：有推理内容但还没有主要内容
  const isThinking = Boolean(reasoningContent && !hasMainContent);

  // 判断是否应该显示计划：有主要内容就显示（无论是否还在流式传输）
  const shouldShowPlan = hasMainContent;
  const handleAccept = useCallback(async () => {
    if (onSendMessage) {
      onSendMessage(
        `${GREETINGS[Math.floor(Math.random() * GREETINGS.length)]}! ${Math.random() > 0.5 ? "让我们开始吧。" : "开始吧。"}`,
        {
          interruptFeedback: "accepted",
        },
      );
    }
  }, [onSendMessage]);
  return (
    <div className={cn("w-full", className)}>
      {reasoningContent && (
        <ThoughtBlock
          content={reasoningContent}
          isStreaming={isThinking}
          hasMainContent={hasMainContent}
        />
      )}
      {shouldShowPlan && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, ease: "easeOut" }}
        >
          <Card className="w-full">
            <CardHeader>
              <CardTitle>
                <Markdown animated={message.isStreaming}>
                  {`### ${
                    plan.title !== undefined && plan.title !== ""
                      ? plan.title
                      : t("deepResearch")
                  }`}
                </Markdown>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div style={{ wordBreak: 'break-all', whiteSpace: 'normal' }}>
                <Markdown className="opacity-80" animated={message.isStreaming}>
                  {plan.thought}
                </Markdown>
                {plan.steps && (
                  <ul className="my-2 flex list-decimal flex-col gap-4 border-l-[2px] pl-8">
                    {plan.steps.map((step, i) => (
                      <li key={`step-${i}`} style={{ wordBreak: 'break-all', whiteSpace: 'normal' }}>
                        <div className="flex items-start gap-2">
                          <div className="flex-1">
                            <h3 className="mb flex items-center gap-2 text-lg font-medium">
                              <Markdown animated={message.isStreaming}>
                                {step.title}
                              </Markdown>
                              {step.tools && step.tools.length > 0 && (
                                <Tooltip
                                  title={`Uses ${step.tools.length} MCP tool${step.tools.length > 1 ? "s" : ""}`}
                                >
                                  <div className="flex items-center gap-1 rounded-full bg-blue-100 px-2 py-1 text-xs text-blue-800">
                                    <Wrench size={12} />
                                    <span>{step.tools.length}</span>
                                  </div>
                                </Tooltip>
                              )}
                            </h3>
                            <div className="text-muted-foreground text-sm" style={{ wordBreak: 'break-all', whiteSpace: 'normal' }}>
                              <Markdown animated={message.isStreaming}>
                                {step.description}
                              </Markdown>
                            </div>
                            {step.tools && step.tools.length > 0 && (
                              <ToolsDisplay tools={step.tools} />
                            )}
                          </div>
                        </div>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </CardContent>
            <CardFooter className="flex justify-end">
              {!message.isStreaming && interruptMessage?.options?.length && (
                <motion.div
                  className="flex gap-2"
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.3, delay: 0.3 }}
                >
                  {interruptMessage?.options.map((option) => (
                    <Button
                      key={option.value}
                      variant={
                        option.value === "accepted" ? "default" : "outline"
                      }
                      disabled={!waitForFeedback}
                      onClick={() => {
                        if (option.value === "accepted") {
                          void handleAccept();
                        } else {
                          onFeedback?.({
                            option,
                          });
                        }
                      }}
                    >
                      {option.text}
                    </Button>
                  ))}
                </motion.div>
              )}
            </CardFooter>
          </Card>
        </motion.div>
      )}
    </div>
  );
}

function PodcastCard({
  className,
  message,
}: {
  className?: string;
  message: Message;
}) {
  const data = useMemo(() => {
    return JSON.parse(message.content ?? "");
  }, [message.content]);
  const title = useMemo<string | undefined>(() => data?.title, [data]);
  const audioUrl = useMemo<string | undefined>(() => data?.audioUrl, [data]);
  const isGenerating = useMemo(() => {
    return message.isStreaming;
  }, [message.isStreaming]);
  const hasError = useMemo(() => {
    return data?.error !== undefined;
  }, [data]);
  const [isPlaying, setIsPlaying] = useState(false);
  return (
    <Card className={cn("w-[508px]", className)}>
      <CardHeader>
        <div className="text-muted-foreground flex items-center justify-between text-sm">
          <div className="flex items-center gap-2">
            {isGenerating ? <LoadingOutlined /> : <Headphones size={16} />}
            {!hasError ? (
              <RainbowText animated={isGenerating}>
                {isGenerating
                  ? "Generating podcast..."
                  : isPlaying
                    ? "Now playing podcast..."
                    : "Podcast"}
              </RainbowText>
            ) : (
              <div className="text-red-500">
                Error when generating podcast. Please try again.
              </div>
            )}
          </div>
          {!hasError && !isGenerating && (
            <div className="flex">
              <Tooltip title="Download podcast">
                <Button variant="ghost" size="icon" asChild>
                  <a
                    href={audioUrl}
                    download={`${(title ?? "podcast").replaceAll(" ", "-")}.mp3`}
                  >
                    <Download size={16} />
                  </a>
                </Button>
              </Tooltip>
            </div>
          )}
        </div>
        <CardTitle>
          <div className="text-lg font-medium">
            <RainbowText animated={isGenerating}>{title}</RainbowText>
          </div>
        </CardTitle>
      </CardHeader>
      <CardContent>
        {audioUrl ? (
          <audio
            className="w-full"
            src={audioUrl}
            controls
            onPlay={() => setIsPlaying(true)}
            onPause={() => setIsPlaying(false)}
          />
        ) : (
          <div className="w-full"></div>
        )}
      </CardContent>
    </Card>
  );
}

function ToolsDisplay({ tools }: { tools: string[] }) {
  return (
    <div className="mt-2 flex flex-wrap gap-1">
      {tools.map((tool, index) => (
        <span
          key={index}
          className="rounded-md bg-muted px-2 py-1 text-xs font-mono text-muted-foreground"
        >
          {tool}
        </span>
      ))}
    </div>
  );
}

/**
 * 问题澄清卡片包装器：管理提交状态，确保卡片提交后不消失
 */
function ClarificationCardWrapper({
  questions,
  onSendMessage,
  alreadySubmitted = false,
}: {
  questions: ClarificationQuestion[];
  onSendMessage?: (
    message: string,
    options?: { interruptFeedback?: string },
  ) => void;
  /** 历史消息中已提交的卡片，直接以只读状态展示 */
  alreadySubmitted?: boolean;
}) {
  const [submitted, setSubmitted] = useState(alreadySubmitted);

  const handleSubmit = useCallback(
    (answers: string[]) => {
      setSubmitted(true);
      // 将多个答案序列化为 JSON 传给后端
      const payload = JSON.stringify(answers);
      onSendMessage?.(payload, { interruptFeedback: payload });
    },
    [onSendMessage],
  );

  return (
    <ClarificationCard
      questions={questions}
      onSubmit={handleSubmit}
      submitted={submitted}
    />
  );
}
