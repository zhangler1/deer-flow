// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

/**
 * Think Tag 解析工具
 *
 * 从消息 content 字段中分离 💭... 思考标签内容和正文内容。
 * 用于 researcher 阶段（差异化展示）和 reporter 阶段（过滤隐藏）。
 */

/** 解析结果 */
export interface ThinkTagParseResult {
  /** 思考内容（💭...标签内的文本） */
  thinkingContent: string;
  /** 正文内容（标签外的文本） */
  mainContent: string;
}

// 匹配已闭合的 💭... 块（跨行，非贪婪）
const CLOSED_THINK_TAG_RE = /<think>([\s\S]*?)<\/think>/g;

// 检测是否存在未闭合的开标签
const OPEN_TAG_RE = /<think>/;

/**
 * 从文本中分离 💭... 思考内容和正文内容
 *
 * 处理逻辑：
 * 1. 先用正则提取所有已闭合的 💭... 块，收集思考内容，移除标签及内容
 * 2. 检查剩余文本中是否存在未闭合的 💭 开标签：
 *    - 如果存在，将开标签后的内容也归入 thinkingContent（流式中"正在思考"状态）
 * 3. 返回分离后的结果
 */
export function parseThinkTags(content: string): ThinkTagParseResult {
  if (!content) {
    return { thinkingContent: "", mainContent: "" };
  }

  const thinkingParts: string[] = [];
  const mainParts: string[] = [];

  // 第一步：提取所有已闭合的 💭... 块
  let lastIndex = 0;
  let match: RegExpExecArray | null;

  // 重置正则 lastIndex
  CLOSED_THINK_TAG_RE.lastIndex = 0;

  while ((match = CLOSED_THINK_TAG_RE.exec(content)) !== null) {
    // 闭标签之前、上一次匹配之后的内容 → 正文
    const beforeTag = content.slice(lastIndex, match.index);
    if (beforeTag) {
      mainParts.push(beforeTag);
    }

    // 闭标签内的内容 → 思考
    const thinkContent = match[1]?.trim();
    if (thinkContent) {
      thinkingParts.push(thinkContent);
    }

    lastIndex = match.index + match[0].length;
  }

  // 剩余部分（最后一个闭标签之后的内容）
  let remaining = content.slice(lastIndex);

  // 第二步：检查是否有未闭合的开标签
  const openMatch = OPEN_TAG_RE.exec(remaining);
  if (openMatch) {
    const beforeOpen = remaining.slice(0, openMatch.index);
    if (beforeOpen) {
      mainParts.push(beforeOpen);
    }

    // 开标签之后的内容 → 思考（流式中正在思考）
    const unclosedThink = remaining.slice(openMatch.index + openMatch[0].length).trim();
    if (unclosedThink) {
      thinkingParts.push(unclosedThink);
    }
  } else {
    // 没有未闭合标签，剩余内容全部是正文
    if (remaining) {
      mainParts.push(remaining);
    }
  }

  return {
    thinkingContent: thinkingParts.join("\n"),
    mainContent: mainParts.join(""),
  };
}

/**
 * 移除文本中所有 💭... 标签及其内容，仅保留正文
 *
 * 与 parseThinkTags 不同，此函数适用于 reporter 阶段需要完全隐藏思考内容的场景，
 * 包括流式输出中未闭合的思考标签块。
 */
export function stripThinkTags(content: string): string {
  if (!content) {
    return "";
  }

  // 第一步：移除所有已闭合的 💭... 块
  let result = content.replace(CLOSED_THINK_TAG_RE, "");

  // 第二步：移除未闭合的开标签及其后内容
  const openMatch = OPEN_TAG_RE.exec(result);
  if (openMatch) {
    result = result.slice(0, openMatch.index);
  }

  return result.trimStart();
}
