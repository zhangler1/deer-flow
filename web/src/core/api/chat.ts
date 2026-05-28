// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

import { env } from "~/env";

import type { MCPServerMetadata } from "../mcp";
import type { Resource } from "../messages";
import { extractReplayIdFromSearchParams } from "../replay/get-replay-id";
import { fetchStream } from "../sse";
import { sleep } from "../utils";
import { withBasePath } from "../utils/base-path";

import { resolveServiceURL } from "./resolve-service-url";
import type { ChatEvent } from "./types";

export async function* chatStream(
  userMessage: string,
  params: {
    thread_id: string;
    resources?: Array<Resource>;
    auto_accepted_plan: boolean;
    max_plan_iterations: number;
    max_step_num: number;
    max_search_results?: number;
    search_engine?: string;
    useBudgetControlledOnlineSearch?: boolean;  // Budget控制的在线检索
    useBudgetControlledBocomSearch?: boolean;   // Budget控制的Bocom搜索
    interrupt_feedback?: string;
    enable_deep_thinking?: boolean;
    enable_background_investigation: boolean;
    report_style?: "academic" | "popular_science" | "news" | "social_media" | "business_marketing" | "business_marketing_client" | "industry_report" | "industry_research";
    reporter_model?: string;  // REPORTER_MODEL_OPTIONS 中的 key
    force_routing_path?: "direct_answer" | "simple_search" | "iterative_research" | "deep_research"; // 🐛 调试模式
    mcp_settings?: {
      servers: Record<
        string,
        MCPServerMetadata & {
          enabled_tools: string[];
          add_to_agents: string[];
        }
      >;
    };
    guwpToken?: string;
  },
  options: { abortSignal?: AbortSignal } = {},
) {
  if (
    env.NEXT_PUBLIC_STATIC_WEBSITE_ONLY ||
    location.search.includes("mock") ||
    location.search.includes("replay=")
  ) 
    return yield* chatReplayStream(userMessage, params, options);
  
  const stream = fetchStream(resolveServiceURL("chat/stream"), {
    body: JSON.stringify({
      messages: [{ role: "user", content: userMessage }],
      ...params,
      guwp_token: params.guwpToken,
    }),
    signal: options.abortSignal,
  });
  
  for await (const event of stream) {
    try {
      // 心跳 ping 事件仅用于保持连接活跃，不需要传递给消费者
      if (event.event === "ping") {
        continue;
      }
      yield {
        type: event.event,
        data: JSON.parse(event.data),
      } as ChatEvent;
    } catch (parseError) {
      console.error("[chatStream] Failed to parse SSE event, skipping", {
        event,
        error: parseError,
        errorName: (parseError as Error).name,
        errorMessage: (parseError as Error).message,
        errorStack: (parseError as Error).stack,
        rawData: event.data,
        rawDataLength: event.data?.length || 0,
        rawDataType: typeof event.data,
        rawDataTypeIsString: typeof event.data === 'string',
        rawDataTypeIsNull: event.data === null,
        rawDataTypeIsUndefined: event.data === undefined,
        eventType: event.event,
        // 打印完整的原始数据（如果不太长）
        ...(event.data && event.data.length < 1000 ? { fullRawData: event.data } : {}),
        // 如果数据较长，打印前500字符和后200字符
        ...(event.data && event.data.length >= 1000 ? {
          rawDataPrefix: event.data.substring(0, 500),
          rawDataSuffix: event.data.substring(event.data.length - 200),
        } : {}),
      });
      // 跳过此事件，继续处理后续事件
      // 如果想完全中断流，可以取消注释下面的 throw
      // throw new Error(
      //   `SSE数据解析失败: ${(parseError as Error).message}\n原始数据: ${event.data?.substring(0, 100)}...`
      // );
      continue;
    }
  }
}

async function* chatReplayStream(
  userMessage: string,
  params: {
    thread_id: string;
    auto_accepted_plan: boolean;
    max_plan_iterations: number;
    max_step_num: number;
    max_search_results?: number;
    interrupt_feedback?: string;
  } = {
    thread_id: "__mock__",
    auto_accepted_plan: false,
    max_plan_iterations: 3,
    max_step_num: 1,
    max_search_results: 2,
    interrupt_feedback: undefined,
  },
  options: { abortSignal?: AbortSignal } = {},
): AsyncIterable<ChatEvent> {
  const urlParams = new URLSearchParams(window.location.search);
  let replayFilePath = "";
  if (urlParams.has("mock")) {
    if (urlParams.get("mock")) {
      replayFilePath = withBasePath(`/mock/${urlParams.get("mock")!}.txt`);
    } else {
      if (params.interrupt_feedback === "accepted") {
        replayFilePath = withBasePath("/mock/final-answer.txt");
      } else if (params.interrupt_feedback === "edit_plan") {
        replayFilePath = withBasePath("/mock/re-plan.txt");
      } else {
        replayFilePath = withBasePath("/mock/first-plan.txt");
      }
    }
    fastForwardReplaying = true;
  } else {
    const replayId = extractReplayIdFromSearchParams(window.location.search);
    if (replayId) {
      replayFilePath = withBasePath(`/replay/${replayId}.txt`);
    } else {
      // Fallback to a default replay
      replayFilePath = withBasePath(`/replay/eiffel-tower-vs-tallest-building.txt`);
    }
  }
  const text = await fetchReplay(replayFilePath, {
    abortSignal: options.abortSignal,
  });
  const normalizedText = text.replace(/\r\n/g, "\n");
  const chunks = normalizedText.split("\n\n");
  for (const chunk of chunks) {
    const [eventRaw, dataRaw] = chunk.split("\n") as [string, string];
    const [, event] = eventRaw.split("event: ", 2) as [string, string];
    const [, data] = dataRaw.split("data: ", 2) as [string, string];

    try {
      const chatEvent = {
        type: event,
        data: JSON.parse(data),
      } as ChatEvent;
      if (chatEvent.type === "message_chunk") {
        if (!chatEvent.data.finish_reason) {
          await sleepInReplay(50);
        }
      } else if (chatEvent.type === "tool_call_result") {
        await sleepInReplay(500);
      }
      yield chatEvent;
      if (chatEvent.type === "tool_call_result") {
        await sleepInReplay(800);
      } else if (chatEvent.type === "message_chunk") {
        if (chatEvent.data.role === "user") {
          await sleepInReplay(500);
        }
      }
    } catch (e) {
      console.error(e);
    }
  }
}

const replayCache = new Map<string, string>();
export async function fetchReplay(
  url: string,
  options: { abortSignal?: AbortSignal } = {},
) {
  if (replayCache.has(url)) {
    return replayCache.get(url)!;
  }
  const res = await fetch(url, {
    signal: options.abortSignal,
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch replay: ${res.statusText}`);
  }
  const text = await res.text();
  replayCache.set(url, text);
  return text;
}

export async function fetchReplayTitle() {
  const res = chatReplayStream(
    "",
    {
      thread_id: "__mock__",
      auto_accepted_plan: false,
      max_plan_iterations: 3,
      max_step_num: 1,
      max_search_results: 2,
    },
    {},
  );
  for await (const event of res) {
    if (event.type === "message_chunk") {
      return event.data.content;
    }
  }
}

export async function sleepInReplay(ms: number) {
  if (fastForwardReplaying) {
    await sleep(0);
  } else {
    await sleep(ms);
  }
}

let fastForwardReplaying = false;
export function fastForwardReplay(value: boolean) {
  fastForwardReplaying = value;
}
