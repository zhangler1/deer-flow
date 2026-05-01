// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

import { nanoid } from "nanoid";
import { toast } from "sonner";
import { create } from "zustand";
import { useShallow } from "zustand/react/shallow";

import { chatStream, generatePodcast } from "../api";
import type { Message, Resource } from "../messages";
import { mergeMessage } from "../messages";
import { parseJSON } from "../utils";

import { getChatStreamSettings } from "./settings-store";

const THREAD_ID = nanoid();

export const useStore = create<{
  responding: boolean;
  threadId: string | undefined;
  messageIds: string[];
  messages: Map<string, Message>;
  researchIds: string[];
  researchPlanIds: Map<string, string>;
  researchReportIds: Map<string, string>;
  researchActivityIds: Map<string, string[]>;
  ongoingResearchId: string | null;
  openResearchId: string | null;
  searchStatus: { query: string; repository?: string } | null;
  // 为每个消息ID维护独立的搜索状态
  messageSearchStatus: Map<string, { query: string; repository?: string } | null>;
  // 迭代研究轮次管理：记录每个消息所属的轮次和轮次状态
  iterationRounds: Map<string, { iteration: number; messageIds: string[]; collapsed: boolean }>;
  currentIteration: number;
  // 保存每个消息的状态显示历史（用于在组件卸载后恢复状态文本）
  messageDisplayStates: Map<string, {
    hasShownSearching: boolean;
    hasShownCrawling: boolean;
    hasShownRoundProgress: boolean;
    preservedRoundText?: string;
    preservedSearchKeywords: string[];
    preservedCrawlUrls: string[];
  }>;

  appendMessage: (message: Message) => void;
  updateMessage: (message: Message) => void;
  updateMessages: (messages: Message[]) => void;
  openResearch: (researchId: string | null) => void;
  closeResearch: () => void;
  setOngoingResearch: (researchId: string | null) => void;
  setSearchStatus: (status: { query: string; repository?: string } | null) => void;
  // 为特定消息设置搜索状态
  setMessageSearchStatus: (messageId: string, status: { query: string; repository?: string } | null) => void;
  // 迭代研究轮次管理方法
  addMessageToCurrentRound: (messageId: string) => void;
  collapseRound: (iteration: number) => void;
  startNewRound: (iteration: number) => void;
  // 更新消息显示状态
  updateMessageDisplayState: (messageId: string, state: Partial<{
    hasShownSearching: boolean;
    hasShownCrawling: boolean;
    hasShownRoundProgress: boolean;
    preservedRoundText?: string;
    preservedSearchKeywords: string[];
    preservedCrawlUrls: string[];
  }>) => void;
}>((set) => ({
  responding: false,
  threadId: THREAD_ID,
  messageIds: [],
  messages: new Map<string, Message>(),
  researchIds: [],
  researchPlanIds: new Map<string, string>(),
  researchReportIds: new Map<string, string>(),
  researchActivityIds: new Map<string, string[]>(),
  ongoingResearchId: null,
  openResearchId: null,
  searchStatus: null,
  messageSearchStatus: new Map<string, { query: string; repository?: string } | null>(),
  iterationRounds: new Map<string, { iteration: number; messageIds: string[]; collapsed: boolean }>(),
  currentIteration: 0,
  messageDisplayStates: new Map(),

  appendMessage(message: Message) {
    set((state) => ({
      messageIds: [...state.messageIds, message.id],
      messages: new Map(state.messages).set(message.id, message),
    }));
  },
  updateMessage(message: Message) {
    set((state) => ({
      messages: new Map(state.messages).set(message.id, message),
    }));
  },
  updateMessages(messages: Message[]) {
    set((state) => {
      const newMessages = new Map(state.messages);
      messages.forEach((m) => newMessages.set(m.id, m));
      return { messages: newMessages };
    });
  },
  openResearch(researchId: string | null) {
    set({ openResearchId: researchId });
  },
  closeResearch() {
    set({ openResearchId: null });
  },
  setOngoingResearch(researchId: string | null) {
    set({ ongoingResearchId: researchId });
  },
  setSearchStatus(status: { query: string; repository?: string } | null) {
    set({ searchStatus: status });
  },
  setMessageSearchStatus(messageId: string, status: { query: string; repository?: string } | null) {
    set((state) => ({
      messageSearchStatus: new Map(state.messageSearchStatus).set(messageId, status),
    }));
  },
  addMessageToCurrentRound(messageId: string) {
    set((state) => {
      const currentIteration = state.currentIteration;
      const key = `round_${currentIteration}`;
      const currentRound = state.iterationRounds.get(key) ?? {
        iteration: currentIteration,
        messageIds: [],
        collapsed: false,
      };
      
      if (!currentRound.messageIds.includes(messageId)) {
        const newRounds = new Map(state.iterationRounds);
        newRounds.set(key, {
          ...currentRound,
          messageIds: [...currentRound.messageIds, messageId],
        });
        return { iterationRounds: newRounds };
      }
      return {};
    });
  },
  collapseRound(iteration: number) {
    set((state) => {
      const key = `round_${iteration}`;
      const round = state.iterationRounds.get(key);
      if (round) {
        const newRounds = new Map(state.iterationRounds);
        newRounds.set(key, { ...round, collapsed: true });
        return { iterationRounds: newRounds };
      }
      return {};
    });
  },
  startNewRound(iteration: number) {
    set((state) => {
      const key = `round_${iteration}`;
      const newRounds = new Map(state.iterationRounds);
      newRounds.set(key, {
        iteration,
        messageIds: [],
        collapsed: false,
      });
      return {
        currentIteration: iteration,
        iterationRounds: newRounds,
      };
    });
  },
  updateMessageDisplayState(messageId: string, stateUpdate: Partial<{
    hasShownSearching: boolean;
    hasShownCrawling: boolean;
    hasShownRoundProgress: boolean;
    preservedRoundText?: string;
    preservedSearchKeywords: string[];
    preservedCrawlUrls: string[];
  }>) {
    set((state) => {
      const currentState = state.messageDisplayStates.get(messageId) ?? {
        hasShownSearching: false,
        hasShownCrawling: false,
        hasShownRoundProgress: false,
        preservedSearchKeywords: [],
        preservedCrawlUrls: [],
      };
      const newStates = new Map(state.messageDisplayStates);
      newStates.set(messageId, {
        ...currentState,
        ...stateUpdate,
      });
      return { messageDisplayStates: newStates };
    });
  },
}));

export async function sendMessage(
  content?: string,
  {
    interruptFeedback,
    resources,
  }: {
    interruptFeedback?: string;
    resources?: Array<Resource>;
  } = {},
  options: { abortSignal?: AbortSignal } = {},
) {
  // 重置迭代研究轮次状态
  // console.log('[轮次重置] 用户发送新消息，重置迭代研究状态');
  useStore.setState({
    currentIteration: 0,
    iterationRounds: new Map(),
    // 注意：不清空 messageDisplayStates，保留旧的显示状态
  });
  
  if (content != null) {
    appendMessage({
      id: nanoid(),
      threadId: THREAD_ID,
      role: "user",
      content: content,
      contentChunks: [content],
      resources,
    });
  }

  const settings = getChatStreamSettings();
  const stream = chatStream(
    content ?? "[REPLAY]",
    {
      thread_id: THREAD_ID,
      interrupt_feedback: interruptFeedback,
      resources,
      auto_accepted_plan: settings.autoAcceptedPlan,
      enable_deep_thinking: settings.enableDeepThinking ?? false,
      enable_background_investigation:
        settings.enableBackgroundInvestigation ?? true,
      max_plan_iterations: settings.maxPlanIterations,
      max_step_num: settings.maxStepNum,
      max_search_results: settings.maxSearchResults,
      search_engine: settings.searchEngine,
      useBudgetControlledOnlineSearch: settings.useBudgetControlledOnlineSearch,  // 新增
      useBudgetControlledBocomSearch: settings.useBudgetControlledBocomSearch,    // 新增
      report_style: settings.reportStyle,
      force_routing_path: settings.forceRoutingPath, // 🐛 调试模式
      mcp_settings: settings.mcpSettings,
    },
    options,
  );

  setResponding(true);
  let messageId: string | undefined;
  // Batch UI updates to reduce re-render frequency during streaming
  const pending = new Map<string, Message>();
  let flushTimer: number | null = null;
  let eventCount = 0;
  let lastEventTime = Date.now();

  const flushNow = () => {
    if (pending.size) {
      useStore.getState().updateMessages(Array.from(pending.values()));
      pending.clear();
    }
  };
  const scheduleFlush = () => {
    if (flushTimer != null) return;
    flushTimer = window.setTimeout(() => {
      flushNow();
      flushTimer = null;
    }, 100);
  };

  // console.log("[sendMessage] Starting to process stream...");

  try {
    for await (const event of stream) {
      const { type, data } = event;
      eventCount++;
      const now = Date.now();
      const timeSinceLastEvent = now - lastEventTime;
      lastEventTime = now;

      // removed verbose: Event received log

      // 处理后端发来的 error 事件
      if (type === "error") {
        const errorMsg = data.error ?? "服务端发生错误";
        console.error("[sendMessage] Backend error event received", {
          thread_id: data.thread_id,
          error: errorMsg,
          errorType: typeof data.error,
          errorLength: data.error?.length,
          fullData: data,
          allKeys: Object.keys(data),
          allValues: Object.values(data),
        });
        // 只有当确实有错误信息时才显示 toast
        if (data.error && data.error.length > 0) {
          toast(`后端错误: ${errorMsg}`);
        }
        // 不 break，继续处理后续事件
        continue;
      }
      
      // Handle search status events
      if (type === "search_status") {
        if (data.status === "started") {
          useStore.getState().setSearchStatus({
            query: data.query,
            repository: data.repository,
          });
          // 同时为当前消息设置搜索状态
          if (data.id) {
            useStore.getState().setMessageSearchStatus(data.id, {
              query: data.query,
              repository: data.repository,
            });
          }
        } else if (data.status === "completed") {
          useStore.getState().setSearchStatus(null);
          // 清除当前消息的搜索状态
          if (data.id) {
            useStore.getState().setMessageSearchStatus(data.id, null);
          }
        }
        continue;
      }
      
      // Handle node transition events (迭代研究节点跳转)
      if (type === "node_transition") {
        // removed verbose: node transition log
        
        // 处理轮次切换逻辑
        const currentIteration = useStore.getState().currentIteration;

      // 如果是继续迭代（iteration增加了），需要折叠当前轮次并开始新轮次
        // console.log(`[轮次切换] 从第${currentIteration}轮切换到第${data.iteration}轮`);
        // 折叠当前轮次
        if (currentIteration > 0) {
          // console.log(`[轮次折叠] 折叠第${currentIteration}轮`);
          useStore.getState().collapseRound(currentIteration);
        }
        // 开始新轮次
        // console.log(`[轮次创建] 创建第${data.iteration}轮研究容器`);
        useStore.getState().startNewRound(data.iteration);
        
        continue;
      }
      
      messageId = data.id;
      let message: Message | undefined;
      if (type === "tool_call_result") {
        message = findMessageByToolCallId(data.tool_call_id);
      } else if (!existsMessage(messageId)) {
        message = {
          id: messageId,
          threadId: data.thread_id,
          agent: data.agent as Message["agent"], // 类型断言修复类型不匹配问题
          role: data.role,
          content: "",
          contentChunks: [],
          reasoningContent: "",
          reasoningContentChunks: [],
          isStreaming: true,
          interruptFeedback,
        };
        // 只有当message不为undefined时才调用appendMessage
        if (message) {
          appendMessage(message);
        }
      }
      message ??= getMessage(messageId);
      if (message) {
        message = mergeMessage(message, event);
        // Batch the updates to reduce CPU usage
        pending.set(message.id, message);
        scheduleFlush();
      }
    }
  } catch (error) {
    // 区分用户主动取消和真实错误
    const isAborted =
      (error instanceof DOMException && error.name === "AbortError") ||
      (error instanceof Error && error.name === "AbortError");

    if (isAborted) {
      // 用户主动取消，不弹错误提示
      console.info("[sendMessage] Stream aborted by user");
    } else {
      const errMsg = (error as Error).message ?? "未知错误";
      console.error("[sendMessage] Streaming error caught", {
        error,
        message: errMsg,
        stack: (error as Error).stack,
        messageId,
        totalEventsProcessed: eventCount,
      });
      toast(`生成回答时出错: ${errMsg}`);
    }
    // Update message status.
    if (messageId != null) {
      const message = getMessage(messageId);
      if (message?.isStreaming) {
        message.isStreaming = false;
        useStore.getState().updateMessage(message);
      }
    }
    // Ensure any pending updates are flushed on error
    flushNow();
    useStore.getState().setOngoingResearch(null);
  } finally {
    // Flush any remaining batched updates before finishing
    flushNow();
    setResponding(false);
    // console.log("[sendMessage] Stream processing ended", {
    //   totalEventsProcessed: eventCount,
    //   duration: Date.now() - lastEventTime,
    // });
  }
}

function setResponding(value: boolean) {
  useStore.setState({ responding: value });
}

function existsMessage(id: string) {
  return useStore.getState().messageIds.includes(id);
}

function getMessage(id: string) {
  return useStore.getState().messages.get(id);
}

function findMessageByToolCallId(toolCallId: string) {
  return Array.from(useStore.getState().messages.values())
    .reverse()
    .find((message) => {
      if (message.toolCalls) {
        return message.toolCalls.some((toolCall) => toolCall.id === toolCallId);
      }
      return false;
    });
}

function appendMessage(message: Message) {
  if (
    message.agent === "coder" ||
    message.agent === "reporter" ||
    message.agent === "researcher"
  ) {
    if (!getOngoingResearchId()) {
      const id = message.id;
      appendResearch(id);
      openResearch(id);
    }
    appendResearchActivity(message);
  }
  
  // 如果是迭代研究节点的消息，添加到当前轮次
  if (message.agent === "iterative_research_node") {
    const currentIteration = useStore.getState().currentIteration;
    // 如果还没有开始轮次，先开始第1轮
    if (currentIteration === 0) {
      useStore.getState().startNewRound(1);
    }
    useStore.getState().addMessageToCurrentRound(message.id);
  }
  
  useStore.getState().appendMessage(message);
}

function updateMessage(message: Message) {
  if (
    getOngoingResearchId() &&
    message.agent === "reporter" &&
    !message.isStreaming
  ) {
    useStore.getState().setOngoingResearch(null);
  }
  useStore.getState().updateMessage(message);
}

function getOngoingResearchId() {
  return useStore.getState().ongoingResearchId;
}

function appendResearch(researchId: string) {
  let planMessage: Message | undefined;
  const reversedMessageIds = [...useStore.getState().messageIds].reverse();
  for (const messageId of reversedMessageIds) {
    const message = getMessage(messageId);
    if (message?.agent === "planner") {
      planMessage = message;
      break;
    }
  }
  const messageIds = [researchId];
  messageIds.unshift(planMessage!.id);
  useStore.setState({
    ongoingResearchId: researchId,
    researchIds: [...useStore.getState().researchIds, researchId],
    researchPlanIds: new Map(useStore.getState().researchPlanIds).set(
      researchId,
      planMessage!.id,
    ),
    researchActivityIds: new Map(useStore.getState().researchActivityIds).set(
      researchId,
      messageIds,
    ),
  });
}

function appendResearchActivity(message: Message) {
  const researchId = getOngoingResearchId();
  if (researchId) {
    const researchActivityIds = useStore.getState().researchActivityIds;
    const current = researchActivityIds.get(researchId)!;
    if (!current.includes(message.id)) {
      useStore.setState({
        researchActivityIds: new Map(researchActivityIds).set(researchId, [
          ...current,
          message.id,
        ]),
      });
    }
    if (message.agent === "reporter") {
      useStore.setState({
        researchReportIds: new Map(useStore.getState().researchReportIds).set(
          researchId,
          message.id,
        ),
      });
    }
  }
}

export function openResearch(researchId: string | null) {
  useStore.getState().openResearch(researchId);
}

export function closeResearch() {
  useStore.getState().closeResearch();
}

export async function listenToPodcast(researchId: string) {
  const planMessageId = useStore.getState().researchPlanIds.get(researchId);
  const reportMessageId = useStore.getState().researchReportIds.get(researchId);
  if (planMessageId && reportMessageId) {
    const planMessage = getMessage(planMessageId)!;
    const title = parseJSON(planMessage.content, { title: "Untitled" }).title;
    const reportMessage = getMessage(reportMessageId);
    if (reportMessage?.content) {
      appendMessage({
        id: nanoid(),
        threadId: THREAD_ID,
        role: "user",
        content: "Please generate a podcast for the above research.",
        contentChunks: [],
      });
      const podCastMessageId = nanoid();
      const podcastObject = { title, researchId };
      const podcastMessage: Message = {
        id: podCastMessageId,
        threadId: THREAD_ID,
        role: "assistant",
        agent: "podcast",
        content: JSON.stringify(podcastObject),
        contentChunks: [],
        reasoningContent: "",
        reasoningContentChunks: [],
        isStreaming: true,
      };
      appendMessage(podcastMessage);
      // Generating podcast...
      let audioUrl: string | undefined;
      try {
        audioUrl = await generatePodcast(reportMessage.content);
      } catch (e) {
        console.error(e);
        useStore.setState((state) => ({
          messages: new Map(useStore.getState().messages).set(
            podCastMessageId,
            {
              ...state.messages.get(podCastMessageId)!,
              content: JSON.stringify({
                ...podcastObject,
                error: e instanceof Error ? e.message : "Unknown error",
              }),
              isStreaming: false,
            },
          ),
        }));
        toast("An error occurred while generating podcast. Please try again.");
        return;
      }
      useStore.setState((state) => ({
        messages: new Map(useStore.getState().messages).set(podCastMessageId, {
          ...state.messages.get(podCastMessageId)!,
          content: JSON.stringify({ ...podcastObject, audioUrl }),
          isStreaming: false,
        }),
      }));
    }
  }
}

export function useResearchMessage(researchId: string) {
  return useStore(
    useShallow((state) => {
      const messageId = state.researchPlanIds.get(researchId);
      return messageId ? state.messages.get(messageId) : undefined;
    }),
  );
}

export function useMessage(messageId: string | null | undefined) {
  return useStore(
    useShallow((state) =>
      messageId ? state.messages.get(messageId) : undefined,
    ),
  );
}

export function useMessageIds() {
  return useStore(useShallow((state) => state.messageIds));
}

export function useLastInterruptMessage() {
  return useStore(
    useShallow((state) => {
      if (state.messageIds.length >= 2) {
        const lastMessage = state.messages.get(
          state.messageIds[state.messageIds.length - 1]!,
        );
        return lastMessage?.finishReason === "interrupt" ? lastMessage : null;
      }
      return null;
    }),
  );
}

export function useLastFeedbackMessageId() {
  const waitingForFeedbackMessageId = useStore(
    useShallow((state) => {
      if (state.messageIds.length >= 2) {
        const lastMessage = state.messages.get(
          state.messageIds[state.messageIds.length - 1]!,
        );
        if (lastMessage && lastMessage.finishReason === "interrupt") {
          return state.messageIds[state.messageIds.length - 2];
        }
      }
      return null;
    }),
  );
  return waitingForFeedbackMessageId;
}

/**
 * 获取指定消息ID对应的中断消息
 * 用于正确匹配计划消息和其中断消息
 */
export function useInterruptMessageFor(messageId: string | undefined) {
  return useStore(
    useShallow((state) => {
      if (!messageId) return null;

      // 找到该消息在messageIds中的索引
      const messageIndex = state.messageIds.indexOf(messageId);
      if (messageIndex === -1) return null;

      // 检查下一条消息是否存在且是中断消息
      const nextMessageId = state.messageIds[messageIndex + 1];
      if (!nextMessageId) return null;

      const nextMessage = state.messages.get(nextMessageId);
      if (nextMessage?.finishReason === "interrupt") {
        return nextMessage;
      }

      return null;
    }),
  );
}

export function useMessageSearchStatus(messageId: string | undefined) {
  return useStore(
    (state) => messageId ? state.messageSearchStatus.get(messageId) : null,
  );
}

// 默认的消息显示状态（稳定的引用，避免无限循环）
const DEFAULT_MESSAGE_DISPLAY_STATE = {
  hasShownSearching: false,
  hasShownCrawling: false,
  hasShownRoundProgress: false,
  preservedRoundText: undefined,
  preservedSearchKeywords: [],
  preservedCrawlUrls: [],
} as const;

// 获取消息的显示状态（用于恢复折叠框的状态文本）
export function useMessageDisplayState(messageId: string) {
  return useStore(
    useShallow((state) => 
      state.messageDisplayStates.get(messageId) ?? DEFAULT_MESSAGE_DISPLAY_STATE
    ),
  );
}

// 获取轮次信息
export function useIterationRound(iteration: number) {
  return useStore((state) => state.iterationRounds.get(`round_${iteration}`));
}

// 获取所有轮次
export function useAllIterationRounds() {
  return useStore(
    useShallow((state) => {
      const rounds = Array.from(state.iterationRounds.values());
      return rounds.sort((a, b) => a.iteration - b.iteration);
    }),
  );
}

// 获取当前轮次号
export function useCurrentIteration() {
  return useStore((state) => state.currentIteration);
}

export function useToolCalls() {
  return useStore(
    useShallow((state) => {
      return state.messageIds
        ?.map((id) => getMessage(id)?.toolCalls)
        .filter((toolCalls) => toolCalls != null)
        .flat();
    }),
  );
}
