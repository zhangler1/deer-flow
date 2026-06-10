"use client";

// SPDX-License-Identifier: MIT

/**
 * 数据看板页面
 *
 * 展示报告生成统计、每日趋势图、报告列表等信息。
 */

import { useCallback, useEffect, useState } from "react";
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
import { StatsCards } from "~/components/dashboard/stats-cards";
import { DailyChart } from "~/components/dashboard/daily-chart";
import { ReportTable } from "~/components/dashboard/report-table";

export default function DashboardPage() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [dailyStats, setDailyStats] = useState<DailyStat[]>([]);
  const [reports, setReports] = useState<ReportListResponse | null>(null);
  const [user, setUser] = useState<UserInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [filterUserCode, setFilterUserCode] = useState("");
  const [filterStatus, setFilterStatus] = useState("");

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [summaryData, statsData, reportsData, userData] = await Promise.all([
        fetchSummary(),
        fetchDailyStats(),
        fetchReports({ page, page_size: 20, user_code: filterUserCode || undefined, status: filterStatus || undefined }),
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
  }, [page, filterUserCode, filterStatus]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handlePageChange = (newPage: number) => {
    setPage(newPage);
  };

  const handleFilterChange = (userCode: string) => {
    setFilterUserCode(userCode);
    setPage(1);
  };

  const handleStatusFilterChange = (status: string) => {
    setFilterStatus(status);
    setPage(1);
  };

  if (loading && !summary) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="text-gray-500">加载中...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* 当前用户信息 */}
      {user?.is_authenticated && (
        <div className="text-sm text-gray-600 dark:text-gray-400">
          当前用户：{user.user_name}（{user.user_code}）
        </div>
      )}

      {/* 顶部统计卡片 */}
      {summary && <StatsCards summary={summary} />}

      {/* 每日报告量折线图 */}
      <div className="rounded-lg border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800">
        <h2 className="mb-4 text-lg font-medium text-gray-900 dark:text-white">
          最近 30 天报告生成趋势
        </h2>
        <DailyChart data={dailyStats} />
      </div>

      {/* 报告列表 */}
      <div className="rounded-lg border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-medium text-gray-900 dark:text-white">
            报告列表
          </h2>
          <div className="flex items-center gap-2">
            <select
              value={filterStatus}
              onChange={(e) => handleStatusFilterChange(e.target.value)}
              className="rounded-md border border-gray-300 px-3 py-1.5 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white"
            >
              <option value="">全部状态</option>
              <option value="completed">已完成</option>
              <option value="cancelled">已取消</option>
            </select>
            <input
              type="text"
              placeholder="按用户工号筛选"
              value={filterUserCode}
              onChange={(e) => handleFilterChange(e.target.value)}
              className="rounded-md border border-gray-300 px-3 py-1.5 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white"
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
    </div>
  );
}
