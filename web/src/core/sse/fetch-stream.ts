// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

import { type StreamEvent } from "./StreamEvent";

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
  while (true) {
    const { done, value } = await reader.read();
    if (done) {
      break;
    }
    buffer += value;
    while (true) {
      const index = buffer.indexOf("\n\n");
      if (index === -1) {
        break;
      }
      const chunk = buffer.slice(0, index);
      buffer = buffer.slice(index + 2);
      const event = parseEvent(chunk);
      if (event) {
        yield event;
      }
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
