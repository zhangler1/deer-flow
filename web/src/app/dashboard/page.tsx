"use client";

// SPDX-License-Identifier: MIT

/**
 * 数据看板页面
 *
 * 展示报告生成统计、每日趋势图、报告列表等信息。
 */

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useTheme } from "next-themes";

import { AdminManagerDialog } from "~/components/dashboard/admin-manager-dialog";
import { DailyChart } from "~/components/dashboard/daily-chart";
import { ReportTable } from "~/components/dashboard/report-table";
import { StatsCards } from "~/components/dashboard/stats-cards";
import {
  fetchDailyStats,
  fetchReports,
  fetchSummary,
  fetchCurrentUser,
  type DailyStat,
  type DashboardSummary,
  type ReportListResponse,
  type UserInfo,
} from "~/core/api/dashboard";

export default function DashboardPage() {
  const router = useRouter();
  const { resolvedTheme } = useTheme();
  const [mounted, setMounted] = useState(false);
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [dailyStats, setDailyStats] = useState<DailyStat[]>([]);
  const [reports, setReports] = useState<ReportListResponse | null>(null);
  const [user, setUser] = useState<UserInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [authChecked, setAuthChecked] = useState(false);
  const [page, setPage] = useState(1);
  const [filterLoginName, setFilterLoginName] = useState("");
  const [filterUserName, setFilterUserName] = useState("");
  const [filterStatus, setFilterStatus] = useState("");
  const [filterStartDate, setFilterStartDate] = useState("");
  const [filterEndDate, setFilterEndDate] = useState("");
  const [showAdminModal, setShowAdminModal] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  const isDark = mounted && resolvedTheme === "dark";

  // 先检查管理员权限，非管理员直接跳回首页
  useEffect(() => {
    fetchCurrentUser()
      .then((u) => {
        if (!u.is_admin) {
          router.replace("/chat");
        } else {
          setAuthChecked(true);
        }
      })
      .catch(() => router.replace("/chat"));
  }, [router]);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [summaryData, statsData, reportsData, userData] = await Promise.all([
        fetchSummary(),
        fetchDailyStats(),
        fetchReports({
          page,
          page_size: 20,
          login_name: filterLoginName || undefined,
          user_name: filterUserName || undefined,
          status: filterStatus || undefined,
          start_date: filterStartDate || undefined,
          end_date: filterEndDate || undefined,
        }),
        fetchCurrentUser(),
      ]);
      setSummary(summaryData);
      setDailyStats(statsData);
      setReports(reportsData);
      setUser(userData);
    } catch (err) {
      console.error("加载看板数据失败:", err);
    } finally {
      setLoading(false);
    }
  }, [page, filterLoginName, filterUserName, filterStatus, filterStartDate, filterEndDate]);

  useEffect(() => {
    if (authChecked) {
      loadData();
    }
  }, [authChecked, loadData]);

  const handlePageChange = (newPage: number) => {
    setPage(newPage);
  };

  const handleFilterChange = (loginName: string) => {
    setFilterLoginName(loginName);
    setPage(1);
  };

  const handleNameFilterChange = (userName: string) => {
    setFilterUserName(userName);
    setPage(1);
  };

  const handleStatusFilterChange = (status: string) => {
    setFilterStatus(status);
    setPage(1);
  };

  const handleStartDateChange = (date: string) => {
    setFilterStartDate(date);
    setPage(1);
  };

  const handleEndDateChange = (date: string) => {
    setFilterEndDate(date);
    setPage(1);
  };

  // 通用样式常量
  const sectionStyle = {
    border: `1px solid ${isDark ? "rgb(55,65,81)" : "rgb(229,231,235)"}`,
    borderRadius: "0.5rem",
    backgroundColor: isDark ? "rgb(31,41,55)" : "rgb(255,255,255)",
    padding: "1.5rem",
  };

  const headingStyle = {
    fontWeight: 500,
    color: isDark ? "rgb(243,244,246)" : "rgb(17,24,39)",
  };

  const inputStyle = {
    border: `1px solid ${isDark ? "rgb(75,85,99)" : "rgb(209,213,219)"}`,
    borderRadius: "0.375rem",
    padding: "0.375rem 0.5rem",
    fontSize: "0.875rem",
    backgroundColor: isDark ? "rgb(55,65,81)" : "transparent",
    color: isDark ? "rgb(243,244,246)" : "inherit",
  };

  if (loading && !summary) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div style={{ color: "#6b7280" }}>加载中...</div>
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
      {/* 当前用户信息 */}
      {user?.is_authenticated && (
        <div
          className="flex items-center justify-between text-sm"
          style={{
            color: isDark ? "rgb(156,163,175)" : "rgb(107,114,128)",
          }}
        >
          <span>
            当前用户：{user.user_name}（{user.login_name}）
          </span>
          <button
            onClick={() => setShowAdminModal(true)}
            className="rounded-md px-3 py-1.5 text-sm text-white"
            style={{ backgroundColor: "rgb(37,99,235)" }}
          >
            管理员管理
          </button>
        </div>
      )}

      {/* 顶部统计卡片 */}
      {summary && <StatsCards summary={summary} />}

      {/* 每日报告量折线图 */}
      <div style={sectionStyle}>
        <h2 className="mb-4 text-lg" style={headingStyle}>
          最近 30 天报告生成趋势
        </h2>
        <DailyChart data={dailyStats} />
      </div>

      {/* 报告列表 */}
      <div style={sectionStyle}>
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg" style={headingStyle}>
            报告列表
          </h2>
          <div className="flex flex-wrap items-center gap-2">
            <div className="flex items-center gap-1">
              <label
                className="text-xs"
                style={{
                  color: isDark ? "rgb(156,163,175)" : "rgb(107,114,128)",
                }}
              >
                从
              </label>
              <input
                type="date"
                value={filterStartDate}
                onChange={(e) => handleStartDateChange(e.target.value)}
                style={inputStyle}
              />
            </div>
            <div className="flex items-center gap-1">
              <label
                className="text-xs"
                style={{
                  color: isDark ? "rgb(156,163,175)" : "rgb(107,114,128)",
                }}
              >
                至
              </label>
              <input
                type="date"
                value={filterEndDate}
                onChange={(e) => handleEndDateChange(e.target.value)}
                style={inputStyle}
              />
            </div>
            {(filterStartDate || filterEndDate) && (
              <button
                onClick={() => {
                  setFilterStartDate("");
                  setFilterEndDate("");
                  setPage(1);
                }}
                className="rounded-md px-2 py-1.5 text-xs"
                style={{
                  color: isDark ? "rgb(156,163,175)" : "rgb(107,114,128)",
                }}
                onMouseEnter={(e) => {
                  (e.currentTarget as HTMLElement).style.color = isDark
                    ? "rgb(229,231,235)"
                    : "rgb(55,65,81)";
                  (e.currentTarget as HTMLElement).style.backgroundColor =
                    isDark ? "rgb(55,65,81)" : "rgb(243,244,246)";
                }}
                onMouseLeave={(e) => {
                  (e.currentTarget as HTMLElement).style.color = isDark
                    ? "rgb(156,163,175)"
                    : "rgb(107,114,128)";
                  (e.currentTarget as HTMLElement).style.backgroundColor = "";
                }}
              >
                清除日期
              </button>
            )}
            <select
              value={filterStatus}
              onChange={(e) => handleStatusFilterChange(e.target.value)}
              style={inputStyle}
            >
              <option value="">全部状态</option>
              <option value="completed">已完成</option>
              <option value="cancelled">已取消</option>
            </select>
            <input
              type="text"
              placeholder="按姓名筛选"
              value={filterUserName}
              onChange={(e) => handleNameFilterChange(e.target.value)}
              style={inputStyle}
            />
            <input
              type="text"
              placeholder="按OA筛选"
              value={filterLoginName}
              onChange={(e) => handleFilterChange(e.target.value)}
              style={inputStyle}
            />
          </div>
        </div>
        {reports && (
          <ReportTable
            data={reports}
            onPageChange={handlePageChange}
          />
        )}
      </div>

      {showAdminModal && (
        <AdminManagerDialog
          isDark={isDark}
          onClose={() => setShowAdminModal(false)}
        />
      )}
    </div>
  );
}
