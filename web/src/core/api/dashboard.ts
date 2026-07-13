// SPDX-License-Identifier: MIT

/**
 * Dashboard API 客户端
 *
 * 封装看板相关的后端 API 调用。
 */

import { resolveServiceURL } from "./resolve-service-url";
import { fetchStream } from "../sse";
import type { ChatEvent } from "./types";
import { useSettingsStore, userInfoReady } from "../store/settings-store";

/**
 * 从 settings store 读取 userInfo，构造 X-User-Info 请求头。
 * await userInfoReady 确保 GuipAPI globalInfo 已就绪，避免组件 mount 时发请求早于 userInfo 写入。
 * 超时 3s 后自动降级（globalInfo 不可用时走 cookie 认证）。
 */
async function authHeaders(): Promise<Record<string, string>> {
  await userInfoReady;
  const userInfo = useSettingsStore.getState().tokens.userInfo;
  if (!userInfo) return {};
  return { "X-User-Info": encodeURIComponent(JSON.stringify(userInfo)) };
}

// ─── 类型定义 ───

export interface DailyStat {
  date: string;
  count: number;
  total_duration_ms: number | null;
  avg_duration_ms: number | null;
}

export interface DashboardSummary {
  total_reports: number;
  today_reports: number;
  month_reports: number;
  mau: number;
  dau: number;
  avg_duration_ms: number;
  avg_tokens: number;
}

export interface ReportRecord {
  id: string;
  thread_id: string | null;
  user_code: string;
  user_name: string | null;
  branch_id: number | null;
  login_name: string | null;
  linked_org_name: string | null;
  title: string;
  duration_ms: number | null;
  report_url: string | null;
  object_name: string | null;
  file_size: number | null;
  report_type: string;
  status: string;
  estimated_tokens: number | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface ReportListResponse {
  items: ReportRecord[];
  total: number;
  page: number;
  page_size: number;
}

export interface UserInfo {
  user_code: string;
  user_name: string;
  branch_id: number | null;
  login_name: string;
  device: string;
  is_authenticated: boolean;
  is_admin: boolean;
}

// ─── API 函数 ───

export async function fetchDailyStats(
  startDate?: string,
  endDate?: string
): Promise<DailyStat[]> {
  const params = new URLSearchParams();
  if (startDate) params.set("start_date", startDate);
  if (endDate) params.set("end_date", endDate);

  const url = resolveServiceURL(`dashboard/stats/daily?${params.toString()}`);
  const resp = await fetch(url, { credentials: "include", headers: await authHeaders() });
  if (!resp.ok) throw new Error(`Failed to fetch daily stats: ${resp.status}`);
  return resp.json();
}

export async function fetchSummary(): Promise<DashboardSummary> {
  const url = resolveServiceURL("dashboard/stats/summary");
  const resp = await fetch(url, { credentials: "include", headers: await authHeaders() });
  if (!resp.ok) throw new Error(`Failed to fetch summary: ${resp.status}`);
  return resp.json();
}

export async function fetchReports(params: {
  page?: number;
  page_size?: number;
  login_name?: string;
  user_name?: string;
  status?: string;
  start_date?: string;
  end_date?: string;
}): Promise<ReportListResponse> {
  const searchParams = new URLSearchParams();
  if (params.page) searchParams.set("page", String(params.page));
  if (params.page_size) searchParams.set("page_size", String(params.page_size));
  if (params.login_name) searchParams.set("login_name", params.login_name);
  if (params.user_name) searchParams.set("user_name", params.user_name);
  if (params.status) searchParams.set("status", params.status);
  if (params.start_date) searchParams.set("start_date", params.start_date);
  if (params.end_date) searchParams.set("end_date", params.end_date);

  const url = resolveServiceURL(`dashboard/reports?${searchParams.toString()}`);
  const resp = await fetch(url, { credentials: "include", headers: await authHeaders() });
  if (!resp.ok) throw new Error(`Failed to fetch reports: ${resp.status}`);
  return resp.json();
}

export async function fetchCurrentUser(): Promise<UserInfo> {
  const url = resolveServiceURL("dashboard/user/me");
  const resp = await fetch(url, { credentials: "include", headers: await authHeaders() });
  if (!resp.ok) throw new Error(`Failed to fetch user: ${resp.status}`);
  return resp.json();
}

// ─── 用户历史报告 API ───

export interface ReportContentResponse {
  content: string;
  title: string;
  report_url: string | null;
}

export interface ContinueReportResponse {
  report_content: string;
  title: string;
}

export async function fetchMyReports(params: {
  page?: number;
  page_size?: number;
  keyword?: string;
  status?: string;
  start_date?: string;
  end_date?: string;
}): Promise<ReportListResponse> {
  const searchParams = new URLSearchParams();
  if (params.page) searchParams.set("page", String(params.page));
  if (params.page_size) searchParams.set("page_size", String(params.page_size));
  if (params.keyword) searchParams.set("keyword", params.keyword);
  if (params.status) searchParams.set("status", params.status);
  if (params.start_date) searchParams.set("start_date", params.start_date);
  if (params.end_date) searchParams.set("end_date", params.end_date);

  const url = resolveServiceURL(`reports/my?${searchParams.toString()}`);
  const resp = await fetch(url, { credentials: "include", headers: await authHeaders() });
  if (!resp.ok) throw new Error(`Failed to fetch my reports: ${resp.status}`);
  return resp.json();
}

export async function fetchReportContent(reportId: string): Promise<ReportContentResponse> {
  const url = resolveServiceURL(`reports/${reportId}/content`);
  const resp = await fetch(url, { credentials: "include", headers: await authHeaders() });
  if (!resp.ok) throw new Error(`Failed to fetch report content: ${resp.status}`);
  return resp.json();
}

export async function continueReport(reportId: string): Promise<ContinueReportResponse> {
  const url = resolveServiceURL(`reports/${reportId}/continue`);
  const resp = await fetch(url, {
    method: "POST",
    credentials: "include",
    headers: await authHeaders(),
  });
  if (!resp.ok) throw new Error(`Failed to continue report: ${resp.status}`);
  return resp.json();
}

export interface SaveReportResponse {
  success: boolean;
  object_name: string;
  file_size: number;
}

export async function saveReportContent(
  reportId: string,
  content: string,
): Promise<SaveReportResponse> {
  const url = resolveServiceURL(`reports/${reportId}`);
  const resp = await fetch(url, {
    method: "PUT",
    credentials: "include",
    headers: { "Content-Type": "application/json", ...(await authHeaders()) },
    body: JSON.stringify({ content }),
  });
  if (!resp.ok) throw new Error(`Failed to save report: ${resp.status}`);
  return resp.json();
}

// ─── 基于历史报告的直连 LLM 流式对话 ───

/**
 * 基于历史报告直接调用 reporter LLM 流式对话。
 * 绕过 coordinator/planner/researcher，返回与 /api/chat/stream 相同格式的 SSE 事件。
 */
export async function* reportChatStream(
  reportId: string,
  message: string,
  params?: {
    history?: Array<{ role: string; content: string }>;
    reporter_model?: string;
  },
  options?: { abortSignal?: AbortSignal },
): AsyncGenerator<ChatEvent> {
  const url = resolveServiceURL(`reports/${reportId}/chat`);
  const headers = await authHeaders();
  const stream = fetchStream(url, {
    body: JSON.stringify({
      message,
      history: params?.history ?? [],
      reporter_model: params?.reporter_model ?? "",
    }),
    signal: options?.abortSignal,
    headers,
  });

  for await (const event of stream) {
    if (event.event === "ping") continue;
    try {
      // 防御性检查：跳过无 data 的事件
      if (!event.data) {
        console.warn("[reportChatStream] Skipping event with null data:", event.event);
        continue;
      }
      const parsed = JSON.parse(event.data);
      if (!parsed) {
        console.warn("[reportChatStream] Parsed data is null:", event);
        continue;
      }
      yield {
        type: event.event,
        data: parsed,
      } as ChatEvent;
    } catch (e) {
      console.error("[reportChatStream] Failed to parse SSE event", event, e);
    }
  }
}
