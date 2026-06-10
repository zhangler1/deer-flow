// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

/**
 * 工具名称中文翻译映射
 * 如果工具名不在此映射中，将使用原始工具名
 * 
 * 使用方法：
 * 1. 在下面的映射对象中添加新的工具名翻译
 * 2. 格式："工具英文名": "工具中文名"
 * 3. 前端会自动使用翻译后的名称显示
 * 
 * 示例：
 * domain_fin_search: "金融知识库搜索",
 * my_custom_tool: "我的自定义工具",
 */
export const TOOL_NAME_TRANSLATIONS: Record<string, string> = {
  // 搜索工具
  web_search: "网络搜索",
  domain_fin_search: "金融知识库搜索",
  local_search_tool: "本地搜索",
  online_search: "外网搜索",
  industry_report_search: "搜索行研报告",
  research_skill_prompt_search: "匹配提示词",
  product_search: "基础产品搜索",
  product_instance_search: "产品实例搜索",
  news_search: "新闻搜索",
  news_detail_search: "新闻详情搜索",
  vector_search: "向量搜索",

  // 爬虫工具
  crawl_tool: "网页爬取",
  batch_crawl_tool: "批量网页爬取",

  // 代码执行工具
  python_repl_tool: "Python 代码执行",

  // RAG 工具
  retriever_tool: "知识库检索",

  // MCP 工具（示例）
  filesystem_read: "文件系统读取",
  filesystem_write: "文件系统写入",
  github_search: "GitHub 搜索",

  // 其他工具可以在这里添加
};

/**
 * 获取工具的中文名称
 * @param toolName 工具的英文名称
 * @returns 中文名称，如果没有翻译则返回原始名称
 */
export function getToolDisplayName(toolName: string): string {
  return TOOL_NAME_TRANSLATIONS[toolName] ?? toolName;
}

/**
 * 获取工具的显示文本
 * @param toolName 工具的英文名称
 * @returns 格式化的显示文本，如 "金融知识库搜索"
 */
export function getToolDisplayText(toolName: string): string {
  return `${getToolDisplayName(toolName)}`;
}
