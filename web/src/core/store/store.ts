// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

import { nanoid } from "nanoid";
import { toast } from "sonner";
import { create } from "zustand";
import { useShallow } from "zustand/react/shallow";

import { chatStream, generatePodcast } from "../api";
import type { Message, Resource } from "../messages";
import { mergeMessage } from "../messages";
import { useSourceStore, type SourceDetail } from "../source-store";
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
  // 报告生成计时状态
  researchStartTime: number | null;
  researchPhase: string;
  researchTotalSteps: number;
  researchCurrentStep: number;
  estimatedDurationMs: number;
  // 里程碑数据（每个 researcher 步骤完成时追加，reporter 完成时单独记录）
  researchMilestones: Array<{ title: string; completedAt: number }>;
  reporterCompletedAt: number | null;
  // 抽屉状态
  drawerOpen: boolean;
  toggleDrawer: () => void;
  // 历史报告回看状态
  viewingReportId: string | null;
  viewingReportContent: string | null;
  viewingReportTitle: string | null;
  openReportViewer: (reportId: string, content: string, title: string) => void;
  closeReportViewer: () => void;

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
  // 报告生成计时状态初始值
  researchStartTime: null,
  researchPhase: "",
  researchTotalSteps: 0,
  researchCurrentStep: -1,
  estimatedDurationMs: 120_000, // 默认 2 分钟，会后台拉取真实均值覆盖
  researchMilestones: [],
  reporterCompletedAt: null,
  // 抽屉初始状态
  drawerOpen: false,
  toggleDrawer() {
    set((state) => ({ drawerOpen: !state.drawerOpen }));
  },
  // 历史报告回看初始状态
  viewingReportId: null,
  viewingReportContent: null,
  viewingReportTitle: null,
  openReportViewer(reportId: string, content: string, title: string) {
    set({
      viewingReportId: reportId,
      viewingReportContent: content,
      viewingReportTitle: title,
      drawerOpen: false,
    });
  },
  closeReportViewer() {
    set({
      viewingReportId: null,
      viewingReportContent: null,
      viewingReportTitle: null,
    });
  },

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
    documentContexts,
  }: {
    interruptFeedback?: string;
    resources?: Array<Resource>;
    documentContexts?: Array<{ filename: string; content: string }>;
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
      document_contexts: documentContexts,
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
      reporter_model: settings.reporterModel,
      force_routing_path: settings.forceRoutingPath, // 🐛 调试模式
      mcp_settings: settings.mcpSettings,
      guwpToken: settings.guwpToken,
    },
    options,
  );

  setResponding(true);
  // 开始计时：记录流开始时间，后台拉取历史平均耗时
  useStore.setState({
    researchStartTime: Date.now(),
    researchPhase: "coordinator",
    researchMilestones: [],
    reporterCompletedAt: null,
  });
  // 异步拉取平均耗时（不阻塞流式处理）
  import("../api/duration").then(({ fetchAvgDuration }) => {
    fetchAvgDuration().then((ms: number) => {
      if (ms > 0) useStore.setState({ estimatedDurationMs: ms });
    }).catch(() => {});
  }).catch(() => {});
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

  let _streamAborted = false;
  // 缓存所有步骤标题（从 plan 中一次性获取，按索引查找）
  let _cachedStepTitles: string[] = [];
  // 记录最后一次 researcher 事件到达时间（用于补录最后一步的完成时间）
  let _lastResearcherEventTime = 0;
  try {
    for await (const event of stream) {
      const { type, data } = event;
      eventCount++;
      const now = Date.now();
      const timeSinceLastEvent = now - lastEventTime;
      lastEventTime = now;

      // 调试日志：记录每个事件的类型和关键信息
      if (type === "tool_calls" || type === "tool_call_chunks" || type === "tool_call_result") {
        console.log(`[SSE调试] 收到事件 type=${type} | msgId=${data.id} | agent=${data.agent}`,
          type === "tool_calls" ? `| tool_calls=${JSON.stringify((data as { tool_calls?: Array<{ name?: string; id?: string }> }).tool_calls?.map(tc => `${tc.name}:${tc.id}`))}` : '',
          type === "tool_call_result" ? `| tool_call_id=${(data as { tool_call_id?: string }).tool_call_id}` : '',
        );
      }

      // 处理后端发来的 error 事件
      if (type === "error") {
        const errorMsg = data.error ?? "服务端发生错误";
        // 后端可能携带 error_type（llm_unavailable / timeout / llm_output_invalid / unknown）
        const errorType = (data as { error_type?: string }).error_type;
        console.error("[sendMessage] Backend error event received", {
          thread_id: data.thread_id,
          error: errorMsg,
          error_type: errorType,
          raw: (data as { raw?: string }).raw,
        });
        // 根据分类显示更友好的 toast
        if (errorType === "llm_unavailable") {
          toast.error("大模型服务不可用", {
            description: "连接失败或鉴权异常，请稍后重试。",
          });
        } else if (errorType === "timeout") {
          toast.warning("本次研究超时", {
            description: "请重试，或简化提问后再试。",
          });
        } else if (errorType === "llm_output_invalid") {
          toast.warning("模型返回内容无法解析", {
            description: "请重试。",
          });
        } else if (errorMsg && errorMsg.length > 0) {
          toast.error(errorMsg);
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
      
      // Handle ping events (仅心跳，无 id，直接跳过；同时让后续代码 TS 可收窄 data 到含 id 的事件类型)
      if (type === "ping") {
        continue;
      }

      // Handle phase_progress events (工作流阶段进度，无 id，直接更新 store 计时状态)
      if (type === "phase_progress") {
        const phaseData = data as {
          phase: string;
          step_index: number;
          total_steps: number;
          step_title?: string;
          step_titles?: string[];
        };
        const currentState = useStore.getState();
        const currentPhase = currentState.researchPhase;
        const currentStep = currentState.researchCurrentStep;
        const updates: Record<string, unknown> = {
          researchPhase: phaseData.phase,
          researchCurrentStep: phaseData.step_index,
          researchTotalSteps: phaseData.total_steps,
        };

        // 后端一次性发送所有步骤标题，缓存起来
        if (phaseData.step_titles && phaseData.step_titles.length > 0) {
          _cachedStepTitles = phaseData.step_titles;
        }

        // 辅助函数：从缓存中获取步骤标题
        const getStepTitle = (idx: number) =>
          (idx >= 0 && idx < _cachedStepTitles.length && _cachedStepTitles[idx])
            ? _cachedStepTitles[idx]!
            : `研究步骤 ${idx + 1}`;

        // 检测 researcher 步骤完成：
        // 0) 首次进入 researcher：补录已完成的步骤
        // 1) step_index 增加：前一步完成
        // 2) 切换到 reporter：最后一个 researcher 步骤完成
        const wasResearcher = currentPhase === "researcher";
        const isResearcher = phaseData.phase === "researcher";

        // 记录 researcher 事件到达时间
        if (isResearcher) {
          _lastResearcherEventTime = Date.now();
        }

        // [调试] 打印阶段转换和里程碑记录逻辑
        console.log(`[里程碑调试] phase=${phaseData.phase} step=${phaseData.step_index} was=${currentPhase} curStep=${currentStep} milestones=${currentState.researchMilestones.length} titles=${JSON.stringify(_cachedStepTitles)}`);

        if (!wasResearcher && isResearcher) {
          // 首次进入 researcher 阶段：补录已完成的步骤
          // 后端 next_step_index 可能已将 step_index 推进到 N，
          // 意味着步骤 0 到 N-1 都已完成
          const milestones = [...currentState.researchMilestones];
          const lastCompleted = phaseData.step_index - 1;
          for (let i = milestones.length; i <= lastCompleted; i++) {
            milestones.push({ title: getStepTitle(i), completedAt: Date.now() });
          }
          if (milestones.length > currentState.researchMilestones.length) {
            console.log(`[里程碑调试] → 首次进入researcher，补录 ${milestones.length - currentState.researchMilestones.length} 个步骤`);
            updates.researchMilestones = milestones;
          }
        } else if (wasResearcher && isResearcher) {
          // researcher 内部：step_index 增加表示之前的步骤完成
          if (phaseData.step_index > currentStep && currentStep >= 0) {
            const milestones = [...currentState.researchMilestones];
            for (let i = milestones.length; i < phaseData.step_index; i++) {
              milestones.push({ title: getStepTitle(i), completedAt: Date.now() });
            }
            console.log(`[里程碑调试] → researcher内部，补录 ${milestones.length - currentState.researchMilestones.length} 个步骤`);
            updates.researchMilestones = milestones;
          }
        } else if (wasResearcher && phaseData.phase === "reporter") {
          // 切换到 reporter：补录所有未记录的 researcher 步骤
          const milestones = [...currentState.researchMilestones];
          if (currentStep >= 0 && milestones.length <= currentStep) {
            // 用最后一次 researcher 事件时间作为完成时间（而非当前时间）
            const completeTime = _lastResearcherEventTime || Date.now();
            for (let i = milestones.length; i <= currentStep; i++) {
              milestones.push({ title: getStepTitle(i), completedAt: completeTime });
            }
            console.log(`[里程碑调试] → reporter转换，补录 ${milestones.length - currentState.researchMilestones.length} 个步骤，使用lastResearcherTime=${_lastResearcherEventTime}`);
            updates.researchMilestones = milestones;
          } else {
            console.log(`[里程碑调试] → reporter转换，无需补录 (curStep=${currentStep}, msLen=${milestones.length})`);
          }
        }

        useStore.setState(updates as Parameters<typeof useStore.setState>[0]);
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

      // Handle reference_index events (后端传来的参考文献索引)
      if (type === "reference_index") {
        const refs = (data as { references: Array<{ index: number; url: string; title: string }> }).references;
        if (refs && refs.length > 0) {
          // 将后端的 reference_index 转换为 SourceDetail 格式
          // 仅包含后端能提供权威值的字段：index / url / title / domain / sourceType
          const newRefs: SourceDetail[] = refs.map(r => ({
            index: r.index,
            url: r.url,
            title: r.title,
            domain: r.url ? (() => { try { return new URL(r.url).hostname.replace(/^www\./, ""); } catch { return r.url; } })() : "",
            sourceType: "search" as const,
          }));

          // 合并模式：保留已有 references 中的内容字段（snippet / fullContent / aiSummary / toolName）
          // 避免后端 reference_index 到达时覆盖掉 toolCall 已经提取的详情，导致 drawer 内容丢失。
          // 匹配策略：先按 url 精确匹配；若失败再按 domain+title 启发式匹配（处理 LLM 改写 URL 的情况）。
          const oldRefs = useSourceStore.getState().references;
          const merged = mergeReferencesPreservingContent(newRefs, oldRefs);
          useSourceStore.getState().setReferences(merged);
          console.log('[reference_index] 后端参考文献索引已更新 | 条数:', refs.length, '| 合并后:', merged.length);
          // 打印完整索引列表，便于核对后端推送到前端的链接与编号
          console.groupCollapsed(`[reference_index] 后端推送完整列表（${refs.length} 条）`);
          for (const r of refs) {
            console.log(`  [${r.index}] ${r.title} -> ${r.url}`);
          }
          console.groupEnd();
        }
        continue;
      }
      
      messageId = data.id;
      let message: Message | undefined;
      if (type === "tool_call_result") {
        // 先 flush pending，确保 tool_calls 事件创建的消息已写入 store
        flushNow();
        console.log('[SSE调试] tool_call_result 事件到达 | tool_call_id=', data.tool_call_id, '| content长度=', data.content?.length ?? 0);
        message = findMessageByToolCallId(data.tool_call_id);
        if (!message) {
          // 查看所有消息的 toolCall IDs
          const allToolCallIds: string[] = [];
          for (const msg of useStore.getState().messages.values()) {
            if (msg.toolCalls) {
              for (const tc of msg.toolCalls) {
                allToolCallIds.push(`${tc.name}:${tc.id}`);
              }
            }
          }
          console.warn('[SSE调试] findMessageByToolCallId 未找到! 当前存储的 toolCall IDs:', allToolCallIds);
        } else {
          console.log('[SSE调试] 已匹配到消息, id=', message.id);
        }
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
    _streamAborted = true;
    // 区分用户主动取消和真实错误
    const isAborted =
      (error instanceof DOMException && error.name === "AbortError") ||
      (error instanceof Error && error.name === "AbortError");

    if (isAborted) {
      // 用户主动取消，不弹错误提示
      console.info("[sendMessage] Stream aborted by user");
      // 把所有还在流式中的消息标为终止，停止波浪号 + 尾部追加"已终止"
      // 注意：必须构造新对象，不能 mutate，否则 Zustand/React 浅比较无法触发 re-render
      const store = useStore.getState();
      const updated: Message[] = [];
      for (const id of store.messageIds) {
        const m = store.messages.get(id);
        if (m?.isStreaming) {
          const existing = m.content ?? "";
          const newContent = existing
            ? (existing.endsWith("[已终止]") ? existing : existing + "\n\n**[已终止]**")
            : "**[已终止]**";
          updated.push({
            ...m,
            isStreaming: false,
            finishReason: "stop",
            content: newContent,
          });
        }
      }
      if (updated.length > 0) {
        store.updateMessages(updated);
      }
      store.setOngoingResearch(null);
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
    // 正常完成且处于 reporter 阶段时，记录 reporter 完成时间
    if (!_streamAborted) {
      const currentState = useStore.getState();
      if (
        currentState.researchPhase === "reporter" &&
        currentState.reporterCompletedAt === null
      ) {
        useStore.setState({ reporterCompletedAt: Date.now() });
      }
    }
    // 清除计时状态（保留 researchStartTime 和里程碑时间戳，下次研究开始时清除）
    useStore.setState({
      researchPhase: "",
      researchCurrentStep: -1,
      researchTotalSteps: 0,
    });
    // Flush any remaining batched updates before finishing
    flushNow();
    setResponding(false);
    // 兜底清理：把所有仍在 isStreaming 的消息终止，防止波浪号不消失
    try {
      const store = useStore.getState();
      const updated: Message[] = [];

      // 判断是否存在 interrupt 消息（计划审核/问题澄清等正常中断）
      // 如果有 interrupt，说明图是正常暂停等待用户输入，不应显示"已终止"
      const hasInterruptMessage = Array.from(store.messages.values()).some(
        (m) => m.finishReason === "interrupt",
      );

      for (const id of store.messageIds) {
        const m = store.messages.get(id);
        if (m?.isStreaming) {
          if (hasInterruptMessage) {
            // 正常 interrupt（如计划审核）：仅停止流式动画，不追加终止文本
            updated.push({
              ...m,
              isStreaming: false,
              finishReason: m.finishReason ?? "stop",
            });
          } else {
            // 非正常结束（错误/超时等）：追加"已终止"提示
            const existing = m.content ?? "";
            const newContent = existing
              ? (existing.endsWith("[已终止]") ? existing : existing + "\n\n**[已终止]**")
              : "**[已终止]**";
            updated.push({
              ...m,
              isStreaming: false,
              finishReason: m.finishReason ?? "stop",
              content: newContent,
            });
          }
        }
      }
      if (updated.length > 0) {
        store.updateMessages(updated);
      }
      store.setOngoingResearch(null);

      // 只有在非 interrupt 且确实有消息被打断时，才追加终止提示
      if (!hasInterruptMessage && updated.length > 0) {
        const lastMsgId = store.messageIds[store.messageIds.length - 1];
        const lastMsg = lastMsgId ? store.messages.get(lastMsgId) : undefined;
        if (!lastMsg || lastMsg.agent !== "system" || !lastMsg.content?.includes("研究已停止")) {
          store.appendMessage({
            id: nanoid(),
            threadId: store.threadId ?? "",
            role: "assistant",
            agent: "system",
            content: "● 研究已停止",
            contentChunks: ["● 研究已停止"],
            isStreaming: false,
            finishReason: "stop",
          });
        }
      }
    } catch (e) {
      console.warn("[sendMessage] finally 清理波浪号异常", e);
    }
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

// ── 工具函数 ──────────────────────────────────────────

/**
 * 合并 references：保留已有 references 中的内容字段
 *
 * 背景：
 *   后端 reference_index 事件会重新设置 references，但只包含后端能提供权威值的字段
 *   （index / url / title / domain / sourceType）。如果直接覆盖，前端从 toolCall 中提取的
 *   snippet / fullContent / aiSummary / toolName 会丢失，导致 drawer 打开后看不到内容。
 *
 * 策略：
 *   1. 以 newRefs 为主（保留后端分配的编号 / 标题 / URL）
 *   2. 从 oldRefs 中匹配相同条目，把内容字段合并进来
 *   3. 匹配优先级：
 *      a) url 精确匹配
 *      b) domain + title 规范化匹配（处理 LLM 改写 URL 的情况）
 *   4. oldRefs 中存在但 newRefs 中不存在的条目（如已被去重的"同标题多 URL"情况）会被丢弃
 *      —— 这是有意为之，与后端 reference_index 的语义保持一致
 */
function mergeReferencesPreservingContent(
  newRefs: SourceDetail[],
  oldRefs: SourceDetail[],
): SourceDetail[] {
  if (oldRefs.length === 0) return newRefs;

  // 构建索引：url -> old ref
  const oldByUrl = new Map<string, SourceDetail>();
  // 构建索引：normalized title -> old ref（用于 url 匹配失败时的兜底）
  const oldByTitle = new Map<string, SourceDetail>();

  const normalize = (s: string): string => s.trim().toLowerCase().replace(/\s+/g, " ");
  for (const old of oldRefs) {
    if (old.url) oldByUrl.set(old.url, old);
    const key = `${normalize(old.domain || "")}::${normalize(old.title || "")}`;
    if (old.title || old.domain) oldByTitle.set(key, old);
  }

  return newRefs.map((nr) => {
    const old = (nr.url && oldByUrl.get(nr.url))
      || oldByTitle.get(`${normalize(nr.domain || "")}::${normalize(nr.title || "")}`);
    if (!old) return nr;
    return {
      ...nr,
      snippet: old.snippet ?? nr.snippet,
      fullContent: old.fullContent ?? nr.fullContent,
      aiSummary: old.aiSummary ?? nr.aiSummary,
      toolName: old.toolName ?? nr.toolName,
      sourceType: old.sourceType ?? nr.sourceType,
    };
  });
}
