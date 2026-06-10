"use client";

// SPDX-License-Identifier: MIT

/**
 * 顶部统计卡片组件
 */

import type { DashboardSummary } from "~/core/api/dashboard";

interface StatsCardsProps {
  summary: DashboardSummary;
}

export function StatsCards({ summary }: StatsCardsProps) {
  const cards = [
    {
      title: "总报告数",
      value: summary.total_reports,
      unit: "份",
      color: "text-blue-600",
      bgColor: "bg-blue-50 dark:bg-blue-900/20",
    },
    {
      title: "今日生成",
      value: summary.today_reports,
      unit: "份",
      color: "text-green-600",
      bgColor: "bg-green-50 dark:bg-green-900/20",
    },
    {
      title: "本月生成",
      value: summary.month_reports,
      unit: "份",
      color: "text-teal-600",
      bgColor: "bg-teal-50 dark:bg-teal-900/20",
    },
    {
      title: "平均耗时",
      value: summary.avg_duration_ms
        ? Math.round(summary.avg_duration_ms / 1000)
        : 0,
      unit: "秒",
      color: "text-orange-600",
      bgColor: "bg-orange-50 dark:bg-orange-900/20",
    },
    {
      title: "月活用户",
      value: summary.mau,
      unit: "人",
      color: "text-purple-600",
      bgColor: "bg-purple-50 dark:bg-purple-900/20",
    },
    {
      title: "日活用户",
      value: summary.dau,
      unit: "人",
      color: "text-pink-600",
      bgColor: "bg-pink-50 dark:bg-pink-900/20",
    },
  ];

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
      {cards.map((card) => (
        <div
          key={card.title}
          className={`rounded-lg border border-gray-200 p-5 dark:border-gray-700 ${card.bgColor}`}
        >
          <div className="text-sm font-medium text-gray-600 dark:text-gray-400">
            {card.title}
          </div>
          <div className={`mt-2 text-3xl font-bold ${card.color}`}>
            {card.value.toLocaleString()}
            <span className="ml-1 text-sm font-normal text-gray-500">
              {card.unit}
            </span>
          </div>
        </div>
      ))}
    </div>
  );
}
