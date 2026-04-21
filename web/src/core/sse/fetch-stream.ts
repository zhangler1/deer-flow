// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

import { type StreamEvent } from "./StreamEvent";

/**
 * 超时配置：如果在这个时间内没有收到任何数据，认为连接已断开
 * 默认 900 秒（15 分钟），考虑到深度研究可能需要较长时间
 * 需要与后端 LLM 超时配置保持一致
 */
const STREAM_TIMEOUT_MS = 900000;

/**
 * 创建一个超时 Promise，用于检测连接是否超时
 * 返回一个对象，包含 Promise 和清理函数
 */
function createTimeoutPromise(timeoutMs: number): {
  promise: Promise<never>;
  cleanup: () => void;
} {
  let timeoutId: ReturnType<typeof setTimeout> | null = null;

  const promise = new Promise<never>((_, reject) => {
    timeoutId = setTimeout(() => {
      reject(new Error(`Stream read timeout: No data received for ${timeoutMs}ms`));
    }, timeoutMs);
  });

  const cleanup = () => {
    if (timeoutId !== null) {
      clearTimeout(timeoutId);
      timeoutId = null;
    }
  };

  return { promise, cleanup };
}

export async function* fetchStream(
  url: string,
  init: RequestInit,
): AsyncIterable<StreamEvent> {
  const response = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Cache-Control": "no-cache",
    },
    ...init,
  });
  if (response.status !== 200) {
    // 读取响应体的前面部分以便调试
    let responseBody = "";
    try {
      responseBody = await response.text();
    } catch {
      responseBody = "<无法读取响应体>";
    }
    console.error("[fetchStream] Non-200 response", {
      url,
      status: response.status,
      statusText: response.statusText,
      headers: Object.fromEntries(response.headers.entries()),
      bodyPreview: responseBody.substring(0, 500),
    });
    throw new Error(
      `HTTP ${response.status} ${response.statusText}\nURL: ${url}\n响应体预览: ${responseBody.substring(0, 200)}...`
    );
  }
  // Read from response body, event by event. An event always ends with a '\n\n'.
  const reader = response.body
    ?.pipeThrough(new TextDecoderStream())
    .getReader();
  if (!reader) {
    throw new Error("Response body is not readable");
  }
  let buffer = "";
  let lastDataTime = Date.now();
  let eventCount = 0;
  let totalBytesReceived = 0;

  try {

    while (true) {
      // 创建带超时的读取 Promise
      const readPromise = reader.read();
      const { promise: timeoutPromise, cleanup: cleanupTimeout } = createTimeoutPromise(STREAM_TIMEOUT_MS);

      // 使用 Promise.race 竞争：先返回的胜出
      const result: ReadableStreamReadResult<string> = await Promise.race([readPromise, timeoutPromise]);

      // 清理超时定时器
      cleanupTimeout();

      // 检查是否读取到数据或流结束
      const { done, value } = result;

      if (done) {
        // console.log("[fetchStream] Stream completed normally", {
        //   totalEvents: eventCount,
        //   totalBytes: totalBytesReceived,
        //   duration: Date.now() - lastDataTime,
        // });
        break;
      }

      // 更新最后接收数据的时间
      const now = Date.now();
      const timeSinceLastData = now - lastDataTime;
      lastDataTime = now;

      // 记录接收到的数据
      totalBytesReceived += value.length;
      // console.log("[fetchStream] Data received", {
      //   bytes: value.length,
      //   totalBytes: totalBytesReceived,
      //   timeSinceLastData: `${timeSinceLastData}ms`,
      //   preview: value.substring(0, 200),
      // });

      // 处理接收到的数据
      buffer += value;
      let eventsParsedInThisChunk = 0;
      while (true) {
        const index = buffer.indexOf("\n\n");
        if (index === -1) {
          break;
        }
        const chunk = buffer.slice(0, index);
        buffer = buffer.slice(index + 2);
        const event = parseEvent(chunk);
        if (event) {
          eventCount++;
          eventsParsedInThisChunk++;
          // console.log("[fetchStream] Event parsed", {
          //   eventNumber: eventCount,
          //   eventType: event.event,
          //   dataLength: event.data?.length || 0,
          //   dataPreview: event.data?.substring(0, 100),
          // });
          yield event;
        }
      }

      if (eventsParsedInThisChunk > 0) {
        // console.log("[fetchStream] Events in this chunk", {
        //   count: eventsParsedInThisChunk,
        //   remainingBufferSize: buffer.length,
        // });
      }
    }
  } catch (error) {
    // 捕获并处理读取错误
    const errorMsg = error instanceof Error ? error.message : String(error);
    console.error("[fetchStream] Stream read error", {
      error,
      errorMessage: errorMsg,
      url,
      timeSinceLastData: Date.now() - lastDataTime,
    });

    // 重新抛出错误，让上层处理
    throw new Error(
      `SSE stream interrupted: ${errorMsg}\n` +
      `Time since last data: ${Date.now() - lastDataTime}ms\n` +
      `URL: ${url}`
    );
  } finally {
    // 确保 reader 被正确关闭
    try {
      await reader.cancel();
    } catch (e) {
      console.warn("[fetchStream] Error canceling reader", e);
    }
  }
}

function parseEvent(chunk: string) {
  let resultEvent = "message";
  let resultData: string | null = null;
  for (const line of chunk.split("\n")) {
    const pos = line.indexOf(": ");
    if (pos === -1) {
      continue;
    }
    const key = line.slice(0, pos);
    const value = line.slice(pos + 2);
    if (key === "event") {
      resultEvent = value;
    } else if (key === "data") {
      resultData = value;
    }
  }
  if (resultEvent === "message" && resultData === null) {
    return undefined;
  }
  return {
    event: resultEvent,
    data: resultData,
  } as StreamEvent;
}
