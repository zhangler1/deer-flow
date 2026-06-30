"use client";

// SPDX-License-Identifier: MIT

/**
 * 报告列表表格组件
 *
 * 展示报告列表，支持分页、Token 列。
 */

import type { ReportListResponse } from "~/core/api/dashboard";

interface ReportTableProps {
  data: ReportListResponse;
  onPageChange: (page: number) => void;
}

/**
 * 格式化 token 数量（>= 1000 显示为 "xk"）
 */
function formatTokens(tokens: number | null | undefined): string {
  if (tokens == null || tokens <= 0) return "-";
  if (tokens >= 1000) {
    return `${(tokens / 1000).toFixed(1)}k`;
  }
  return String(tokens);
}

export function ReportTable({ data, onPageChange }: ReportTableProps) {
  const { items, total, page, page_size } = data;
  const totalPages = Math.ceil(total / page_size);

  /**
   * 格式化耗时（毫秒转为可读字符串）
   */
  function formatDuration(ms: number | null): string {
    if (!ms) return "-";
    if (ms < 1000) return `${ms}ms`;
    const seconds = Math.round(ms / 1000);
    if (seconds < 60) return `${seconds}秒`;
    const minutes = Math.floor(seconds / 60);
    const remainSec = seconds % 60;
    return `${minutes}分${remainSec}秒`;
  }

  /**
   * 格式化时间
   */
  function formatTime(dateStr: string | null): string {
    if (!dateStr) return "-";
    const d = new Date(dateStr);
    return d.toLocaleString("zh-CN", {
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });
  }

  if (items.length === 0) {
    return (
      <div className="py-8 text-center text-gray-400">暂无报告数据</div>
    );
  }

  return (
    <div>
      {/* 表格 */}
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead className="bg-gray-50 text-xs uppercase text-gray-600 dark:bg-gray-700 dark:text-gray-400">
            <tr>
              <th className="px-4 py-3">用户</th>
              <th className="px-4 py-3">标题</th>
              <th className="px-4 py-3">类型</th>
              <th className="px-4 py-3">状态</th>
              <th className="px-4 py-3">Token</th>
              <th className="px-4 py-3">耗时</th>
              <th className="px-4 py-3">生成时间</th>
              <th className="px-4 py-3">操作</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
            {items.map((report) => (
              <tr
                key={report.id}
                className="hover:bg-gray-50 dark:hover:bg-gray-800"
              >
                <td className="px-4 py-3">
                  <div className="font-medium text-gray-900 dark:text-white">
                    {report.user_name || report.user_code}
                  </div>
                  <div className="text-xs text-gray-500">
                    {report.user_code}
                  </div>
                </td>
                <td className="max-w-[240px] truncate px-4 py-3 text-gray-900 dark:text-white">
                  {report.title}
                </td>
                <td className="px-4 py-3">
                  <span className="rounded-full bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-800 dark:bg-blue-900 dark:text-blue-300">
                    {report.report_type}
                  </span>
                </td>
                <td className="px-4 py-3">
                  {report.status === "completed" ? (
                    <span className="rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-800 dark:bg-green-900 dark:text-green-300">
                      已完成
                    </span>
                  ) : report.status === "cancelled" ? (
                    <span className="rounded-full bg-yellow-100 px-2 py-0.5 text-xs font-medium text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300">
                      已取消
                    </span>
                  ) : (
                    <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-800 dark:bg-gray-900 dark:text-gray-300">
                      {report.status}
                    </span>
                  )}
                </td>
                <td className="px-4 py-3 text-gray-600 dark:text-gray-400">
                  <span
                    className={
                      (report.estimated_tokens ?? 0) > 10000
                        ? "font-medium text-orange-600 dark:text-orange-400"
                        : ""
                    }
                    title={
                      report.estimated_tokens
                        ? `${report.estimated_tokens.toLocaleString()} tokens`
                        : "暂无数据"
                    }
                  >
                    {formatTokens(report.estimated_tokens)}
                  </span>
                </td>
                <td className="px-4 py-3 text-gray-600 dark:text-gray-400">
                  {formatDuration(report.duration_ms)}
                </td>
                <td className="px-4 py-3 text-gray-600 dark:text-gray-400">
                  {formatTime(report.created_at)}
                </td>
                <td className="px-4 py-3">
                  {report.report_url ? (
                    <a
                      href={report.report_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-blue-600 hover:underline dark:text-blue-400"
                    >
                      查看
                    </a>
                  ) : (
                    <span className="text-gray-400">-</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* 分页 */}
      {totalPages > 1 && (
        <div className="mt-4 flex items-center justify-between">
          <div className="text-sm text-gray-600 dark:text-gray-400">
            共 {total} 条，第 {page}/{totalPages} 页
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => onPageChange(page - 1)}
              disabled={page <= 1}
              className="rounded-md border border-gray-300 px-3 py-1 text-sm disabled:cursor-not-allowed disabled:opacity-50 dark:border-gray-600"
            >
              上一页
            </button>
            <button
              onClick={() => onPageChange(page + 1)}
              disabled={page >= totalPages}
              className="rounded-md border border-gray-300 px-3 py-1 text-sm disabled:cursor-not-allowed disabled:opacity-50 dark:border-gray-600"
            >
              下一页
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
