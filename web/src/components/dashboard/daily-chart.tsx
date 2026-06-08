"use client";

// SPDX-License-Identifier: MIT

/**
 * 每日报告量折线图组件
 *
 * 使用纯 SVG 实现轻量折线图，无需额外依赖。
 * 如果后续需要更复杂的图表可替换为 recharts。
 */

import type { DailyStat } from "~/core/api/dashboard";

interface DailyChartProps {
  data: DailyStat[];
}

export function DailyChart({ data }: DailyChartProps) {
  if (!data || data.length === 0) {
    return (
      <div className="flex h-48 items-center justify-center text-gray-400">
        暂无数据
      </div>
    );
  }

  // 图表尺寸
  const width = 800;
  const height = 200;
  const padding = { top: 20, right: 30, bottom: 40, left: 50 };
  const chartWidth = width - padding.left - padding.right;
  const chartHeight = height - padding.top - padding.bottom;

  // 计算数据范围
  const maxCount = Math.max(...data.map((d) => d.count), 1);
  const xStep = chartWidth / Math.max(data.length - 1, 1);

  // 生成折线路径
  const points = data.map((d, i) => ({
    x: padding.left + i * xStep,
    y: padding.top + chartHeight - (d.count / maxCount) * chartHeight,
  }));

  const linePath = points
    .map((p, i) => `${i === 0 ? "M" : "L"} ${p.x} ${p.y}`)
    .join(" ");

  // 填充区域路径
  const areaPath = `${linePath} L ${points[points.length - 1]!.x} ${padding.top + chartHeight} L ${points[0]!.x} ${padding.top + chartHeight} Z`;

  // Y 轴刻度
  const yTicks = Array.from({ length: 5 }, (_, i) =>
    Math.round((maxCount / 4) * i)
  );

  return (
    <div className="w-full overflow-x-auto">
      <svg
        viewBox={`0 0 ${width} ${height}`}
        className="w-full min-w-[600px]"
        preserveAspectRatio="xMidYMid meet"
      >
        {/* 网格线 */}
        {yTicks.map((tick) => {
          const y =
            padding.top + chartHeight - (tick / maxCount) * chartHeight;
          return (
            <g key={tick}>
              <line
                x1={padding.left}
                y1={y}
                x2={padding.left + chartWidth}
                y2={y}
                stroke="#e5e7eb"
                strokeDasharray="4 2"
              />
              <text
                x={padding.left - 8}
                y={y + 4}
                textAnchor="end"
                className="fill-gray-500 text-[10px]"
              >
                {tick}
              </text>
            </g>
          );
        })}

        {/* 填充区域 */}
        <path d={areaPath} fill="url(#gradient)" opacity={0.3} />

        {/* 折线 */}
        <path
          d={linePath}
          fill="none"
          stroke="#3b82f6"
          strokeWidth={2}
          strokeLinecap="round"
          strokeLinejoin="round"
        />

        {/* 数据点 */}
        {points.map((p, i) => (
          <circle
            key={i}
            cx={p.x}
            cy={p.y}
            r={3}
            fill="#3b82f6"
            stroke="white"
            strokeWidth={1.5}
          />
        ))}

        {/* X 轴标签（每隔 5 天显示） */}
        {data.map((d, i) => {
          if (i % 5 !== 0 && i !== data.length - 1) return null;
          const x = padding.left + i * xStep;
          const label = d.date.slice(5); // MM-DD
          return (
            <text
              key={i}
              x={x}
              y={padding.top + chartHeight + 20}
              textAnchor="middle"
              className="fill-gray-500 text-[10px]"
            >
              {label}
            </text>
          );
        })}

        {/* 渐变定义 */}
        <defs>
          <linearGradient id="gradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#3b82f6" />
            <stop offset="100%" stopColor="#3b82f6" stopOpacity={0} />
          </linearGradient>
        </defs>
      </svg>
    </div>
  );
}
