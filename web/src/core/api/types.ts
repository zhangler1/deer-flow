// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

import type { ClarificationQuestion, Option } from "../messages";

// Tool Calls

export interface ToolCall {
  type: "tool_call";
  id: string;
  name: string;
  args: Record<string, unknown>;
}

export interface ToolCallChunk {
  type: "tool_call_chunk";
  index: number;
  id: string;
  name: string;
  args: string;
}

// Events

interface GenericEvent<T extends string, D extends object> {
  type: T;
  data: {
    id: string;
    thread_id: string;
    agent: "coordinator" | "planner" | "researcher" | "coder" | "reporter" | "router" | "direct_answer_node" | "simple_search_node" | "domain_knowledge_node";
    role: "user" | "assistant" | "tool";
    finish_reason?: "stop" | "tool_calls" | "interrupt";
    tag?: "routing" | "planning" | "searching" | "crawling" | "iterative_answering" | "reporting" | "waiting_for_feedback" | "error" | "answering" | "round_progress";
    round_text?: string;
    /** 当前 plan step 索引（仅 researcher 消息） */
    step_index?: number;
    /** 当前 plan step 标题（仅 researcher 消息） */
    step_title?: string;
  } & D;
}

export interface MessageChunkEvent
  extends GenericEvent<
    "message_chunk",
    {
      content?: string;
      reasoning_content?: string;
    }
  > {}

export interface ToolCallsEvent
  extends GenericEvent<
    "tool_calls",
    {
      tool_calls: ToolCall[];
      tool_call_chunks: ToolCallChunk[];
    }
  > {}

export interface ToolCallChunksEvent
  extends GenericEvent<
    "tool_call_chunks",
    {
      tool_call_chunks: ToolCallChunk[];
    }
  > {}

export interface ToolCallResultEvent
  extends GenericEvent<
    "tool_call_result",
    {
      tool_call_id: string;
      content?: string;
    }
  > {}

export interface InterruptEvent
  extends GenericEvent<
    "interrupt",
    {
      options?: Option[];
      /** 问卷模式：多个澄清问题 */
      questions?: ClarificationQuestion[];
    }
  > {}

export interface SearchStatusEvent
  extends GenericEvent<
    "search_status",
    {
      query: string;
      repository?: string;
      status: "started" | "completed";
    }
  > {}

export interface NodeTransitionEvent {
  type: "node_transition";
  data: {
    thread_id: string;
    from: string;
    to: string;
    iteration: number;
    reason: string;
  };
}

export interface PingEvent {
  type: "ping";
  data: {
    thread_id: string;
    timestamp: number;
  };
}

export interface ErrorEvent {
  type: "error";
  data: {
    thread_id: string;
    error: string;
  };
}

export interface ReferenceIndexEvent {
  type: "reference_index";
  data: {
    thread_id: string;
    references: Array<{
      index: number;
      url: string;
      title: string;
    }>;
  };
}

export interface PhaseProgressEvent {
  type: "phase_progress";
  data: {
    thread_id: string;
    /** 当前工作流阶段节点名称 */
    phase:
      | "coordinator"
      | "background_investigator"
      | "planner"
      | "researcher"
      | "reporter";
    /** 当前 plan step 索引（researcher 阶段内），-1 表示未知 */
    step_index: number;
    /** plan 中的总步骤数，0 表示未知 */
    total_steps: number;
    /** 当前步骤标题（researcher 阶段内） */
    step_title?: string;
    /** 所有步骤标题（从 plan 中一次性获取，供前端按索引查找） */
    step_titles?: string[];
  };
}

export type ChatEvent =
  | MessageChunkEvent
  | ToolCallsEvent
  | ToolCallChunksEvent
  | ToolCallResultEvent
  | InterruptEvent
  | SearchStatusEvent
  | NodeTransitionEvent
  | PingEvent
  | ErrorEvent
  | ReferenceIndexEvent
  | PhaseProgressEvent;
