"use client";

// SPDX-License-Identifier: MIT

/**
 * 报告列表表格组件
 *
 * 展示报告列表，支持分页、Token 列。
 */

import { useEffect, useState } from "react";
import { useTheme } from "next-themes";

import type { ReportListResponse } from "~/core/api/dashboard";

interface ReportTableProps {
  data: ReportListResponse;
  onPageChange: (page: number) => void;
}

/** 状态徽章色值 */
const STATUS_COLORS: Record<
  string,
  {
    lightBg: string;
    lightText: string;
    darkBg: string;
    darkText: string;
  }
> = {
  completed: {
    lightBg: "#dcfce7",
    lightText: "#166534",
    darkBg: "rgba(20,83,45,0.35)",
    darkText: "#86efac",
  },
  cancelled: {
    lightBg: "#fef9c3",
    lightText: "#854d0e",
    darkBg: "rgba(120,53,15,0.35)",
    darkText: "#fcd34d",
  },
  __default: {
    lightBg: "#f3f4f6",
    lightText: "#1f2937",
    darkBg: "rgba(55,65,81,0.4)",
    darkText: "#d1d5db",
  },
};

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
  const { resolvedTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  const { items, total, page, page_size } = data;
  const totalPages = Math.ceil(total / page_size);
  const isDark = mounted && resolvedTheme === "dark";

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
      <div className="py-8 text-center" style={{ color: "#9ca3af" }}>
        暂无报告数据
      </div>
    );
  }

  return (
    <div>
      {/* 表格 */}
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead
            className="text-xs uppercase"
            style={{
              backgroundColor: isDark
                ? "rgb(55,65,81)"
                : "rgb(249,250,251)",
              color: isDark ? "rgb(156,163,175)" : "rgb(107,114,128)",
            }}
          >
            <tr>
              <th className="px-4 py-3">用户</th>
              <th className="px-4 py-3">标题</th>
              <th className="px-4 py-3">类型</th>
              <th className="px-4 py-3">状态</th>
              <th className="px-4 py-3">Token</th>
              <th className="px-4 py-3">耗时</th>
              <th className="px-4 py-3">生成时间</th>
            </tr>
          </thead>
          <tbody
            style={{
              borderColor: isDark
                ? "rgb(55,65,81)"
                : "rgb(229,231,235)",
            }}
          >
            {items.map((report) => {
              const statusStyle =
                STATUS_COLORS[report.status] ?? STATUS_COLORS.__default!;
              return (
                <tr
                  key={report.id}
                  className="border-b"
                  style={{
                    borderColor: isDark
                      ? "rgb(55,65,81)"
                      : "rgb(229,231,235)",
                  }}
                  onMouseEnter={(e) => {
                    (
                      e.currentTarget as HTMLElement
                    ).style.backgroundColor = isDark
                      ? "rgb(31,41,55)"
                      : "rgb(249,250,251)";
                  }}
                  onMouseLeave={(e) => {
                    (e.currentTarget as HTMLElement).style.backgroundColor =
                      "";
                  }}
                >
                  <td className="px-4 py-3">
                    <div
                      className="font-medium"
                      style={{
                        color: isDark
                          ? "rgb(243,244,246)"
                          : "rgb(17,24,39)",
                      }}
                    >
                      {report.user_name || report.user_code}
                    </div>
                    <div
                      className="text-xs"
                      style={{
                        color: isDark
                          ? "rgb(156,163,175)"
                          : "rgb(107,114,128)",
                      }}
                    >
                      {report.user_code}
                    </div>
                  </td>
                  <td
                    className="max-w-[240px] truncate px-4 py-3"
                    style={{
                      color: isDark
                        ? "rgb(243,244,246)"
                        : "rgb(17,24,39)",
                    }}
                  >
                    {report.title}
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className="rounded-full px-2 py-0.5 text-xs font-medium"
                      style={{
                        backgroundColor: isDark
                          ? "rgba(30,58,95,0.4)"
                          : "#dbeafe",
                        color: isDark ? "#93c5fd" : "#1e40af",
                      }}
                    >
                      {report.report_type}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className="rounded-full px-2 py-0.5 text-xs font-medium"
                      style={{
                        backgroundColor: isDark
                          ? statusStyle.darkBg
                          : statusStyle.lightBg,
                        color: isDark
                          ? statusStyle.darkText
                          : statusStyle.lightText,
                      }}
                    >
                      {report.status === "completed"
                        ? "已完成"
                        : report.status === "cancelled"
                          ? "已取消"
                          : report.status}
                    </span>
                  </td>
                  <td
                    className="px-4 py-3"
                    style={{
                      color: isDark
                        ? "rgb(156,163,175)"
                        : "rgb(107,114,128)",
                    }}
                  >
                    <span
                      style={{
                        fontWeight:
                          (report.estimated_tokens ?? 0) > 10000
                            ? 500
                            : undefined,
                        color:
                          (report.estimated_tokens ?? 0) > 10000
                            ? isDark
                              ? "#fb923c"
                              : "#ea580c"
                            : undefined,
                      }}
                      title={
                        report.estimated_tokens
                          ? `${report.estimated_tokens.toLocaleString()} tokens`
                          : "暂无数据"
                      }
                    >
                      {formatTokens(report.estimated_tokens)}
                    </span>
                  </td>
                  <td
                    className="px-4 py-3"
                    style={{
                      color: isDark
                        ? "rgb(156,163,175)"
                        : "rgb(107,114,128)",
                    }}
                  >
                    {formatDuration(report.duration_ms)}
                  </td>
                  <td
                    className="px-4 py-3"
                    style={{
                      color: isDark
                        ? "rgb(156,163,175)"
                        : "rgb(107,114,128)",
                    }}
                  >
                    {formatTime(report.created_at)}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* 分页 */}
      {totalPages > 1 && (
        <div className="mt-4 flex items-center justify-between">
          <div
            className="text-sm"
            style={{
              color: isDark ? "rgb(156,163,175)" : "rgb(107,114,128)",
            }}
          >
            共 {total} 条，第 {page}/{totalPages} 页
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => onPageChange(page - 1)}
              disabled={page <= 1}
              className="rounded-md px-3 py-1 text-sm disabled:cursor-not-allowed disabled:opacity-50"
              style={{
                border: `1px solid ${isDark ? "rgb(75,85,99)" : "rgb(209,213,219)"}`,
                color: isDark ? "rgb(243,244,246)" : "rgb(17,24,39)",
                backgroundColor: isDark
                  ? "rgb(31,41,55)"
                  : "transparent",
              }}
            >
              上一页
            </button>
            <button
              onClick={() => onPageChange(page + 1)}
              disabled={page >= totalPages}
              className="rounded-md px-3 py-1 text-sm disabled:cursor-not-allowed disabled:opacity-50"
              style={{
                border: `1px solid ${isDark ? "rgb(75,85,99)" : "rgb(209,213,219)"}`,
                color: isDark ? "rgb(243,244,246)" : "rgb(17,24,39)",
                backgroundColor: isDark
                  ? "rgb(31,41,55)"
                  : "transparent",
              }}
            >
              下一页
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
