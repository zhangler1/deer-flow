"use client";

// SPDX-License-Identifier: MIT

/**
 * 顶部统计卡片组件
 */

import { useEffect, useState } from "react";
import { useTheme } from "next-themes";

import { TEMPLATE_TYPE_LABELS } from "~/core/api/dashboard";
import type { DashboardSummary, TemplateStat } from "~/core/api/dashboard";

interface StatsCardsProps {
  summary: DashboardSummary;
  templateStats?: TemplateStat[];
}

/** 各卡片色值（light / dark 文字色 / dark 背景色） */
const CARD_COLORS: Record<
  string,
  { lightText: string; lightBg: string; darkText: string; darkBg: string }
> = {
  blue: {
    lightText: "#2563eb",
    lightBg: "#eff6ff",
    darkText: "#93c5fd",
    darkBg: "rgba(30,58,95,0.22)",
  },
  green: {
    lightText: "#16a34a",
    lightBg: "#f0fdf4",
    darkText: "#86efac",
    darkBg: "rgba(20,83,45,0.22)",
  },
  teal: {
    lightText: "#0d9488",
    lightBg: "#f0fdfa",
    darkText: "#5eead4",
    darkBg: "rgba(19,78,74,0.22)",
  },
  orange: {
    lightText: "#ea580c",
    lightBg: "#fff7ed",
    darkText: "#fdba74",
    darkBg: "rgba(124,45,18,0.22)",
  },
  amber: {
    lightText: "#d97706",
    lightBg: "#fffbeb",
    darkText: "#fcd34d",
    darkBg: "rgba(120,53,15,0.22)",
  },
  purple: {
    lightText: "#9333ea",
    lightBg: "#faf5ff",
    darkText: "#c4b5fd",
    darkBg: "rgba(88,28,135,0.22)",
  },
  pink: {
    lightText: "#db2777",
    lightBg: "#fdf2f8",
    darkText: "#f9a8d4",
    darkBg: "rgba(131,24,67,0.22)",
  },
};

export function StatsCards({ summary, templateStats = [] }: StatsCardsProps) {
  const { resolvedTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  const isDark = mounted && resolvedTheme === "dark";

  const cards = [
    {
      title: "总报告数",
      value: summary.total_reports,
      unit: "份",
      colorKey: "blue",
    },
    {
      title: "今日生成",
      value: summary.today_reports,
      unit: "份",
      colorKey: "green",
    },
    {
      title: "本月生成",
      value: summary.month_reports,
      unit: "份",
      colorKey: "teal",
    },
    {
      title: "平均耗时",
      value: summary.avg_duration_ms
        ? Math.round(summary.avg_duration_ms / 1000)
        : 0,
      unit: "秒",
      colorKey: "orange",
    },
    {
      title: "平均 Token",
      value: summary.avg_tokens ?? 0,
      unit: "枚",
      colorKey: "amber",
    },
    {
      title: "月活用户",
      value: summary.mau,
      unit: "人",
      colorKey: "purple",
    },
    {
      title: "日活用户",
      value: summary.dau,
      unit: "人",
      colorKey: "pink",
    },
  ];

  const colorKeys = Object.keys(CARD_COLORS);

  return (
    <div>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-7">
        {cards.map((card) => {
          const c = CARD_COLORS[card.colorKey]!;
          return (
            <div
              key={card.title}
              className="rounded-lg border p-5"
              style={{
                borderColor: isDark
                  ? "rgba(255,255,255,0.1)"
                  : "rgb(229,231,235)",
                backgroundColor: isDark ? c.darkBg : c.lightBg,
              }}
            >
              <div
                className="text-sm font-medium"
                style={{
                  color: isDark
                    ? "rgb(156,163,175)"
                    : "rgb(107,114,128)",
                }}
              >
                {card.title}
              </div>
              <div
                className="mt-2 text-3xl font-bold"
                style={{ color: isDark ? c.darkText : c.lightText }}
              >
                {card.value.toLocaleString()}
                <span
                  className="ml-1 text-sm font-normal"
                  style={{
                    color: isDark
                      ? "rgb(156,163,175)"
                      : "rgb(107,114,128)",
                  }}
                >
                  {card.unit}
                </span>
              </div>
            </div>
          );
        })}
      </div>

      {/* 各模板统计（Chrome 108 兼容：颜色沿用 CARD_COLORS 的 #hex/rgba 格式） */}
      {templateStats.length > 0 && (
        <div className="mt-4">
          <div
            className="mb-3 text-sm font-medium"
            style={{
              color: isDark ? "rgb(156,163,175)" : "rgb(107,114,128)",
            }}
          >
            模板统计
          </div>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {templateStats.map((stat, index) => {
              const colorKey =
                colorKeys[index % colorKeys.length] ?? "blue";
              const c = CARD_COLORS[colorKey]!;
              const label =
                TEMPLATE_TYPE_LABELS[stat.template_type] ??
                stat.template_type ??
                "未知";
              return (
                <div
                  key={stat.template_type}
                  className="rounded-lg border p-5"
                  style={{
                    borderColor: isDark
                      ? "rgba(255,255,255,0.1)"
                      : "rgb(229,231,235)",
                    backgroundColor: isDark ? c.darkBg : c.lightBg,
                  }}
                >
                  <div
                    className="text-sm font-medium"
                    style={{
                      color: isDark
                        ? "rgb(156,163,175)"
                        : "rgb(107,114,128)",
                    }}
                  >
                    {label}
                  </div>
                  <div className="mt-3 flex items-end justify-center gap-20">
                    <div>
                      <div
                        className="text-3xl font-bold"
                        style={{ color: isDark ? c.darkText : c.lightText }}
                      >
                        {stat.count.toLocaleString()}
                      </div>
                      <div
                        className="mt-0.5 text-xs"
                        style={{
                          color: isDark
                            ? "rgb(156,163,175)"
                            : "rgb(107,114,128)",
                        }}
                      >
                        总数
                      </div>
                    </div>
                    <div>
                      <div
                        className="text-3xl font-bold"
                        style={{ color: isDark ? c.darkText : c.lightText }}
                      >
                        {stat.month_count.toLocaleString()}
                      </div>
                      <div
                        className="mt-0.5 text-xs"
                        style={{
                          color: isDark
                            ? "rgb(156,163,175)"
                            : "rgb(107,114,128)",
                        }}
                      >
                        本月
                      </div>
                    </div>
                    <div>
                      <div
                        className="text-3xl font-bold"
                        style={{ color: isDark ? c.darkText : c.lightText }}
                      >
                        {stat.today_count.toLocaleString()}
                      </div>
                      <div
                        className="mt-0.5 text-xs"
                        style={{
                          color: isDark
                            ? "rgb(156,163,175)"
                            : "rgb(107,114,128)",
                        }}
                      >
                        今日
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
