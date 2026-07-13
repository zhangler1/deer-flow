"use client";

// SPDX-License-Identifier: MIT

/**
 * 每日报告量折线图组件
 *
 * 使用纯 SVG 实现轻量折线图，支持鼠标悬停吸附数据点、虚线指示、tooltip 显示。
 */

import { useCallback, useRef, useState } from "react";

import type { DailyStat } from "~/core/api/dashboard";

interface DailyChartProps {
  data: DailyStat[];
}

export function DailyChart({ data }: DailyChartProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const [activeIndex, setActiveIndex] = useState<number | null>(null);

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

  // 鼠标移动：吸附到最近的数据点
  const handleMouseMove = useCallback(
    (e: React.MouseEvent<SVGSVGElement>) => {
      const svg = svgRef.current;
      if (!svg) return;
      const rect = svg.getBoundingClientRect();
      // 将屏幕坐标转换为 SVG viewBox 坐标
      const scaleX = width / rect.width;
      const svgX = (e.clientX - rect.left) * scaleX;
      // 找到最近的点
      const idx = Math.round((svgX - padding.left) / xStep);
      const clamped = Math.max(0, Math.min(data.length - 1, idx));
      setActiveIndex(clamped);
    },
    [data.length, xStep, padding.left]
  );

  const handleMouseLeave = useCallback(() => {
    setActiveIndex(null);
  }, []);

  const activePoint = activeIndex !== null ? points[activeIndex] : null;
  const activeData = activeIndex !== null ? data[activeIndex] : null;

  return (
    <div className="w-full overflow-x-auto">
      <svg
        ref={svgRef}
        viewBox={`0 0 ${width} ${height}`}
        className="w-full min-w-[600px]"
        preserveAspectRatio="xMidYMid meet"
        onMouseMove={handleMouseMove}
        onMouseLeave={handleMouseLeave}
      >
        {/* 网格线 */}
        {yTicks.map((tick, index) => {
          const y =
            padding.top + chartHeight - (tick / maxCount) * chartHeight;
          return (
            <g key={`ytick-${index}-${tick}`}>
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
                fill="#6b7280"
                className="text-[10px]"
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
            r={activeIndex === i ? 5 : 3}
            fill={activeIndex === i ? "#2563eb" : "#3b82f6"}
            stroke="white"
            strokeWidth={activeIndex === i ? 2 : 1.5}
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
              fill="#6b7280"
              className="text-[10px]"
            >
              {label}
            </text>
          );
        })}

        {/* 悬停指示：垂直虚线 + tooltip */}
        {activePoint && activeData && (
          <>
            {/* 垂直虚线 */}
            <line
              x1={activePoint.x}
              y1={padding.top}
              x2={activePoint.x}
              y2={padding.top + chartHeight}
              stroke="#3b82f6"
              strokeWidth={1}
              strokeDasharray="4 3"
              opacity={0.6}
            />
            {/* 水平虚线 */}
            <line
              x1={padding.left}
              y1={activePoint.y}
              x2={padding.left + chartWidth}
              y2={activePoint.y}
              stroke="#3b82f6"
              strokeWidth={1}
              strokeDasharray="4 3"
              opacity={0.4}
            />
            {/* Tooltip 背景 */}
            <rect
              x={
                activePoint.x + 10 + 90 > width
                  ? activePoint.x - 100
                  : activePoint.x + 10
              }
              y={
                activePoint.y - 36 < 0
                  ? activePoint.y + 8
                  : activePoint.y - 36
              }
              width={90}
              height={30}
              rx={4}
              fill="rgba(17,24,39,0.85)"
            />
            {/* Tooltip 日期 */}
            <text
              x={
                activePoint.x + 10 + 90 > width
                  ? activePoint.x - 55
                  : activePoint.x + 55
              }
              y={
                activePoint.y - 36 < 0
                  ? activePoint.y + 20
                  : activePoint.y - 24
              }
              textAnchor="middle"
              fill="#fff"
              className="text-[10px]"
            >
              {activeData.date}
            </text>
            {/* Tooltip 数量 */}
            <text
              x={
                activePoint.x + 10 + 90 > width
                  ? activePoint.x - 55
                  : activePoint.x + 55
              }
              y={
                activePoint.y - 36 < 0
                  ? activePoint.y + 33
                  : activePoint.y - 11
              }
              textAnchor="middle"
              fill="#fff"
              className="text-[11px] font-bold"
            >
              报告数：{activeData.count}
            </text>
          </>
        )}

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