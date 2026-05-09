// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

export type MessageRole = "user" | "assistant" | "tool";

export interface Message {
  id: string;
  threadId: string;
  agent?:
    | "coordinator"
    | "planner"
    | "researcher"
    | "coder"
    | "reporter"
    | "podcast"
    | "router"
    | "direct_answer_node"
    | "simple_search_node"
    | "iterative_research_node"
    | "iterative_reporter_node"
    | "system";
  role: MessageRole;
  isStreaming?: boolean;
  content: string;
  contentChunks: string[];
  reasoningContent?: string;
  reasoningContentChunks?: string[];
  toolCalls?: ToolCallRuntime[];
  options?: Option[];
  finishReason?: "stop" | "interrupt" | "tool_calls";
  interruptFeedback?: string;
  resources?: Array<Resource>;
  tag?: "routing" | "planning" | "searching" | "crawling" | "iterative_answering" | "reporting" | "waiting_for_feedback" | "error" | "answering" | "round_progress";
  roundText?: string;
  /** 当前 plan step 索引（从0开始，由后端 SSE 事件传入） */
  stepIndex?: number;
  /** 当前 plan step 标题（由后端 SSE 事件传入） */
  stepTitle?: string;
}

export interface Option {
  text: string;
  value: string;
}

export interface ToolCallRuntime {
  id: string;
  name: string;
  args: Record<string, unknown>;
  argsChunks?: string[];
  result?: string;
}

export interface Resource {
  uri: string;
  title: string;
}
