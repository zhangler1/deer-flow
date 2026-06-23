// SPDX-License-Identifier: MIT

/**
 * Dashboard API 客户端
 *
 * 封装看板相关的后端 API 调用。
 */

import { resolveServiceURL } from "./resolve-service-url";

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
}

export interface ReportRecord {
  id: string;
  thread_id: string | null;
  user_code: string;
  user_name: string | null;
  branch_id: number | null;
  login_name: string | null;
  title: string;
  duration_ms: number | null;
  report_url: string | null;
  object_name: string | null;
  file_size: number | null;
  report_type: string;
  status: string;
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
  const resp = await fetch(url, { credentials: "include" });
  if (!resp.ok) throw new Error(`Failed to fetch daily stats: ${resp.status}`);
  return resp.json();
}

export async function fetchSummary(): Promise<DashboardSummary> {
  const url = resolveServiceURL("dashboard/stats/summary");
  const resp = await fetch(url, { credentials: "include" });
  if (!resp.ok) throw new Error(`Failed to fetch summary: ${resp.status}`);
  return resp.json();
}

export async function fetchReports(params: {
  page?: number;
  page_size?: number;
  user_code?: string;
  user_name?: string;
  status?: string;
  start_date?: string;
  end_date?: string;
}): Promise<ReportListResponse> {
  const searchParams = new URLSearchParams();
  if (params.page) searchParams.set("page", String(params.page));
  if (params.page_size) searchParams.set("page_size", String(params.page_size));
  if (params.user_code) searchParams.set("user_code", params.user_code);
  if (params.user_name) searchParams.set("user_name", params.user_name);
  if (params.status) searchParams.set("status", params.status);
  if (params.start_date) searchParams.set("start_date", params.start_date);
  if (params.end_date) searchParams.set("end_date", params.end_date);

  const url = resolveServiceURL(`dashboard/reports?${searchParams.toString()}`);
  const resp = await fetch(url, { credentials: "include" });
  if (!resp.ok) throw new Error(`Failed to fetch reports: ${resp.status}`);
  return resp.json();
}

export async function fetchCurrentUser(): Promise<UserInfo> {
  const url = resolveServiceURL("dashboard/user/me");
  const resp = await fetch(url, { credentials: "include" });
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
  const resp = await fetch(url, { credentials: "include" });
  if (!resp.ok) throw new Error(`Failed to fetch my reports: ${resp.status}`);
  return resp.json();
}

export async function fetchReportContent(reportId: string): Promise<ReportContentResponse> {
  const url = resolveServiceURL(`reports/${reportId}/content`);
  const resp = await fetch(url, { credentials: "include" });
  if (!resp.ok) throw new Error(`Failed to fetch report content: ${resp.status}`);
  return resp.json();
}

export async function continueReport(reportId: string): Promise<ContinueReportResponse> {
  const url = resolveServiceURL(`reports/${reportId}/continue`);
  const resp = await fetch(url, {
    method: "POST",
    credentials: "include",
  });
  if (!resp.ok) throw new Error(`Failed to continue report: ${resp.status}`);
  return resp.json();
}
