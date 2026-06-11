// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

import type {
  ChatEvent,
  InterruptEvent,
  MessageChunkEvent,
  ToolCallChunksEvent,
  ToolCallResultEvent,
  ToolCallsEvent,
} from "../api";
import { deepClone } from "../utils/deep-clone";

import type { Message } from "./types";

export function mergeMessage(message: Message, event: ChatEvent) {
  if (event.type === "message_chunk") {
    mergeTextMessage(message, event);
  } else if (event.type === "tool_calls" || event.type === "tool_call_chunks") {
    mergeToolCallMessage(message, event);
  } else if (event.type === "tool_call_result") {
    mergeToolCallResultMessage(message, event);
  } else if (event.type === "interrupt") {
    mergeInterruptMessage(message, event);
  }
  
  // Update tag if present in event
  if ('tag' in event.data && event.data.tag) {
    message.tag = event.data.tag;
  }
  
  // Update roundText if present in event (for round_progress tag)
  if ('round_text' in event.data && event.data.round_text) {
    message.roundText = event.data.round_text;
  }
  
  // Update stepIndex/stepTitle if present in event (from backend plan step tracking)
  if ('step_index' in event.data && event.data.step_index !== undefined) {
    message.stepIndex = event.data.step_index;
  }
  if ('step_title' in event.data && event.data.step_title) {
    message.stepTitle = event.data.step_title;
  }
  
  if ('finish_reason' in event.data && event.data.finish_reason) {
    message.finishReason = event.data.finish_reason;
    message.isStreaming = false;
    if (message.toolCalls) {
      message.toolCalls.forEach((toolCall) => {
        if (toolCall.argsChunks?.length) {
          const joinedArgs = toolCall.argsChunks.join("");
          try {
            toolCall.args = JSON.parse(joinedArgs);
            delete toolCall.argsChunks;
          } catch (parseError) {
            const errorInfo = {
              toolCallId: toolCall.id,
              toolCallName: toolCall.name,
              argsChunks: toolCall.argsChunks,
              joinedArgs,
              joinedArgsLength: joinedArgs.length,
              // 打印前 200 字符和后 200 字符，看问题在哪
              preview: {
                first200: joinedArgs.substring(0, 200),
                last200: joinedArgs.substring(Math.max(0, joinedArgs.length - 200)),
              },
              parseError: (parseError as Error).message,
              stack: (parseError as Error).stack,
            };
            console.error("[mergeMessage] Failed to parse tool call args");
            console.error("[mergeMessage] RAW_ARGS_START\n" + joinedArgs + "\nRAW_ARGS_END");
            // 尝试修复：如果是多个 JSON 对象，只取第一个
            try {
              const jsonRegex = /^\s*(\{[^]*?\})/;
              const firstJsonMatch = jsonRegex.exec(joinedArgs);
              if (firstJsonMatch?.[1]) {

                toolCall.args = JSON.parse(firstJsonMatch[1]);
                delete toolCall.argsChunks;
              } else {
                // 实在解析不了，保留原始字符串

                toolCall.args = { __raw__: joinedArgs, __parse_error__: (parseError as Error).message };
                delete toolCall.argsChunks;
              }
            } catch (recoveryError) {

              toolCall.args = { __raw__: joinedArgs, __parse_error__: (parseError as Error).message };
              delete toolCall.argsChunks;
            }
          }
        }
      });
    }
  }
  return deepClone(message);
}

function mergeTextMessage(message: Message, event: MessageChunkEvent) {
  if (event.data.content) {
    message.content += event.data.content;
    message.contentChunks.push(event.data.content);
  }
  if (event.data.reasoning_content) {
    message.reasoningContent = (message.reasoningContent ?? "") + event.data.reasoning_content;
    message.reasoningContentChunks = message.reasoningContentChunks ?? [];
    message.reasoningContentChunks.push(event.data.reasoning_content);
  }
}
function convertToolChunkArgs(args: string) {
  // Convert escaped characters in args
  if (!args) return "";
  return args.replace(/&#91;/g, "[").replace(/&#93;/g, "]").replace(/&#123;/g, "{").replace(/&#125;/g, "}");
}
function mergeToolCallMessage(
  message: Message,
  event: ToolCallsEvent | ToolCallChunksEvent,
) {
  if (event.type === "tool_calls" && event.data.tool_calls[0]?.name) {
    const newToolCalls = event.data.tool_calls.map((raw) => ({
      id: raw.id,
      name: raw.name,
      args: raw.args,
      result: undefined,
    }));
    const prevCount = message.toolCalls?.length ?? 0;
    if (prevCount > 0) {
      // ⚠️ 追加模式：已有 toolCalls，合并新的（避免覆盖）
      const existingIds = new Set(message.toolCalls!.map(tc => tc.id));
      const trulyNew = newToolCalls.filter(tc => !existingIds.has(tc.id));
      console.warn('[mergeToolCallMessage] ⚠️ 已有toolCalls被追加!',
        'prevCount=', prevCount,
        'newCount=', newToolCalls.length,
        'trulyNewCount=', trulyNew.length,
        'prevIds=', message.toolCalls!.map(tc => `${tc.name}:${tc.id}`),
        'newIds=', newToolCalls.map(tc => `${tc.name}:${tc.id}`),
        'msgId=', (event.data as { id?: string }).id,
      );
      message.toolCalls = [...message.toolCalls!, ...trulyNew];
    } else {
      console.log('[mergeToolCallMessage] 首次设置 toolCalls |',
        'count=', newToolCalls.length,
        'tools=', newToolCalls.map(tc => `${tc.name}:${tc.id}`).join(', '),
        'msgId=', (event.data as { id?: string }).id,
      );
      message.toolCalls = newToolCalls;
    }
  }

  message.toolCalls ??= [];
  for (const chunk of event.data.tool_call_chunks) {
    if (chunk.id) {
      const toolCall = message.toolCalls.find(
        (toolCall) => toolCall.id === chunk.id,
      );
      if (toolCall) {
        toolCall.argsChunks = [convertToolChunkArgs(chunk.args)];
      } else {
        console.warn('[mergeToolCallMessage] chunk.id 未匹配到任何 toolCall!',
          'chunk.id=', chunk.id, 'chunk.name=', chunk.name,
          '已有IDs=', message.toolCalls.map(tc => tc.id),
        );
      }
    } else {
      // 使用 chunk.index 路由到正确的 toolCall（修复并行工具调用 args 错误合并问题）
      const targetIndex = chunk.index ?? -1;
      let targetToolCall =
        targetIndex >= 0 && targetIndex < message.toolCalls.length
          ? message.toolCalls[targetIndex]
          : undefined;

      // 如果按 index 找到的 toolCall 尚未初始化 argsChunks，则初始化
      if (targetToolCall && !targetToolCall.argsChunks) {
        targetToolCall.argsChunks = [];
      }

      // 回退：如果 index 无效，找最后一个有 argsChunks 的 toolCall
      if (!targetToolCall) {
        for (let i = message.toolCalls.length - 1; i >= 0; i--) {
          if (message.toolCalls[i]?.argsChunks?.length) {
            targetToolCall = message.toolCalls[i];
            break;
          }
        }
      }

      if (targetToolCall?.argsChunks) {
        targetToolCall.argsChunks.push(convertToolChunkArgs(chunk.args));
      }
    }
  }
}

function mergeToolCallResultMessage(
  message: Message,
  event: ToolCallResultEvent,
) {
  const toolCall = message.toolCalls?.find(
    (toolCall) => toolCall.id === event.data.tool_call_id,
  );
  if (toolCall) {
    toolCall.result = event.data.content;
    console.log('[mergeToolCallResult] tool=', toolCall.name, '| result长度=', event.data.content?.length, '| result预览=', event.data.content?.substring(0, 200));
  } else {
    console.warn('[mergeToolCallResult] 未找到 toolCall! tool_call_id=', event.data.tool_call_id);
  }
}

function mergeInterruptMessage(message: Message, event: InterruptEvent) {
  message.isStreaming = false;
  message.finishReason = "interrupt";  // 设置 finishReason 为 interrupt
  message.options = event.data.options;
  // 问卷模式：多问题结构
  if (event.data.questions) {
    message.clarificationQuestions = event.data.questions;
  }
}
