"use client";

import { useEffect, useMemo, useState } from "react";
import { Tooltip } from "~/components/deer-flow/tooltip";
import { useStore } from "~/core/store";
import { cn } from "~/lib/utils";

// ── 阶段配置 ────────────────────────────────────────────────────────────────

/**
 * 进度条只追踪两个阶段（coordinator/planner 等前置阶段不计算进度）：
 *  - researcher: 0–75%（按 step_index/total_steps 插值）
 *  - reporter:   75–100%（报告生成中即视为接近完成）
 */
const RESEARCHER_WEIGHT = 75;
const REPORTER_WEIGHT = 25;

// ── 进度计算 ─────────────────────────────────────────────────────────────────

/**
 * 计算当前进度百分比（0–100）。
 *
 * - researcher 阶段：按 step_index / total_steps 线性插值，占 0–75%
 * - reporter 阶段：固定 75% + 阶段内进度，占 75–100%
 * - coordinator / background_investigator / planner：返回小值（5% / 10% / 15%）
 */
function calcProgress(
  phase: string,
  stepIndex: number,
  totalSteps: number,
): number {
  if (phase === "researcher") {
    if (totalSteps > 0 && stepIndex >= 0) {
      const ratio = Math.min((stepIndex + 1) / totalSteps, 1);
      return Math.min(Math.round(RESEARCHER_WEIGHT * ratio), RESEARCHER_WEIGHT);
    }
    return Math.round(RESEARCHER_WEIGHT * 0.3);
  }

  if (phase === "reporter") {
    return RESEARCHER_WEIGHT + Math.round(REPORTER_WEIGHT * 0.9);
  }

  // 前置阶段：返回小值让进度条可见
  switch (phase) {
    case "coordinator": return 5;
    case "background_investigator": return 10;
    case "planner": return 15;
    default: return 3; // 未知阶段也给一个最小可见值
  }
}

/** 获取当前阶段中文名 */
function getPhaseLabel(phase: string): string {
  switch (phase) {
    case "coordinator":
      return "准备中";
    case "background_investigator":
      return "背景调研";
    case "planner":
      return "生成计划";
    case "researcher":
      return "深度研究";
    case "reporter":
      return "生成报告";
    default:
      return "处理中";
  }
}

// ── 时间格式化 ────────────────────────────────────────────────────────────────

/** 将毫秒格式化为 mm:ss */
function formatElapsed(ms: number): string {
  const totalSec = Math.floor(ms / 1000);
  const m = Math.floor(totalSec / 60);
  const s = totalSec % 60;
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

/** 将时间戳格式化为 HH:MM:SS */
function formatTimestamp(ts: number): string {
  const d = new Date(ts);
  const h = String(d.getHours()).padStart(2, "0");
  const m = String(d.getMinutes()).padStart(2, "0");
  const s = String(d.getSeconds()).padStart(2, "0");
  return `${h}:${m}:${s}`;
}

// ── 里程碑圆点组件 ────────────────────────────────────────────────────────────

function MilestoneDot({
  position,
  title,
  completedAt,
  compact,
  isLast,
}: {
  position: number;
  title: string;
  completedAt: number;
  compact: boolean;
  isLast?: boolean;
}) {
  const size = compact ? 10 : 14;

  return (
    <Tooltip
      title={
        <div className="text-xs max-w-[180px]">
          <div className="font-medium truncate">{title}</div>
          <div className="mt-0.5 text-white/80">
            {formatTimestamp(completedAt)}
          </div>
        </div>
      }
      side={isLast ? "left" : "top"}
      sideOffset={6}
    >
      <div
        className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2 rounded-full border-2 border-white bg-[#22c55e] shadow-sm transition-all duration-300 z-10 cursor-pointer"
        style={{
          left: `${position}%`,
          width: size,
          height: size,
        }}
      />
    </Tooltip>
  );
}

// ── 组件 ──────────────────────────────────────────────────────────────────────

export interface ResearchTimerProps {
  className?: string;
  /** 紧凑模式：用于 ResearchCard 内部，减少内边距 */
  compact?: boolean;
}

/**
 * 报告生成计时进度条（含里程碑）。
 *
 * 展示内容：
 *  - 左侧：当前阶段中文名（仅 researcher / reporter）
 *  - 右侧：已用时间 (mm:ss) · 进度百分比 (XX%)
 *  - 下方：渐变进度条 + 里程碑圆点
 *
 * 里程碑：
 *  - 每个 researcher 步骤完成时追加一个绿色圆点，位置按步骤比例分布在 0–75% 区间
 *  - reporter 完成时在 100% 位置显示"报告生成完毕"圆点
 *  - hover 圆点显示步骤标题和完成时间
 */
export function ResearchTimer({ className, compact = false }: ResearchTimerProps) {
  const startTime = useStore((s) => s.researchStartTime);
  const phase = useStore((s) => s.researchPhase);
  const stepIndex = useStore((s) => s.researchCurrentStep);
  const totalSteps = useStore((s) => s.researchTotalSteps);
  const milestones = useStore((s) => s.researchMilestones);
  const reporterCompletedAt = useStore((s) => s.reporterCompletedAt);

  // 每秒刷新已用时间
  const [tick, setTick] = useState(0);
  useEffect(() => {
    if (!startTime) return;
    const timer = setInterval(() => setTick((t) => t + 1), 1_000);
    return () => clearInterval(timer);
  }, [startTime]);

  const elapsed = useMemo(() => {
    if (!startTime) return 0;
    void tick;
    // 如果 reporter 已完成，用完成时间戳计算总耗时
    if (reporterCompletedAt) {
      return reporterCompletedAt - startTime;
    }
    return Date.now() - startTime;
  }, [startTime, tick, reporterCompletedAt]);

  const hasMilestones = milestones.length > 0 || reporterCompletedAt !== null;

  const progress = useMemo(() => {
    if (reporterCompletedAt !== null) return 100;
    return calcProgress(phase, stepIndex, totalSteps);
  }, [phase, stepIndex, totalSteps, reporterCompletedAt]);

  const phaseLabel = useMemo(() => {
    if (reporterCompletedAt !== null) return "已完成";
    return getPhaseLabel(phase);
  }, [phase, reporterCompletedAt]);

  // 计算已完成步骤数（用于定位里程碑圆点）
  const completedStepCount = milestones.length;
  // 总步骤数：优先用 store 中的值，完成后用里程碑数量
  const effectiveTotalSteps = totalSteps > 0 ? totalSteps : completedStepCount;

  // 没有开始时间且无里程碑时不渲染
  if (!startTime && !hasMilestones) return null;

  return (
    <div className={cn(compact ? "px-2 py-1" : "px-4 py-3", className)}>
      {/* 信息行 */}
      <div className="flex items-center justify-between mb-1">
        <span className={cn(
          "text-xs font-medium",
          reporterCompletedAt ? "text-[#16a34a]" : "text-primary",
        )}>
          {phaseLabel}
        </span>
        <span className="text-[11px] tabular-nums text-muted-foreground">
          {formatElapsed(elapsed)}
          <span className="mx-1 text-muted-foreground/50">·</span>
          <span className={cn(
            "font-medium",
            reporterCompletedAt ? "text-[#16a34a]" : "text-primary",
          )}>
            {progress}%
          </span>
        </span>
      </div>

      {/* 进度条（含里程碑圆点） */}
      <div className={cn(
        "relative w-full rounded-full bg-[rgba(2,101,220,0.15)] dark:bg-[rgba(52,168,235,0.2)]",
        compact ? "h-1" : "h-1.5",
        compact ? "my-1.5" : "my-2",
      )}>
        {/* 进度条填充 */}
        <div
          className={cn(
            "absolute inset-y-0 left-0 rounded-full transition-all duration-500 ease-out",
            reporterCompletedAt ? "bg-[#22c55e]" : "bg-primary",
          )}
          style={{ width: `${progress}%` }}
        />
        {/* 微光动画叠加层（仅在进行中时显示） */}
        {!reporterCompletedAt && progress > 0 && (
          <div
            className="absolute inset-y-0 left-0 rounded-full opacity-40 animate-pulse"
            style={{
              width: `${progress}%`,
              background:
                "linear-gradient(90deg, transparent, rgba(255,255,255,0.5), transparent)",
            }}
          />
        )}

        {/* 里程碑圆点：每个已完成的 researcher 步骤 */}
        {milestones.map((ms, i) => {
          // 位置：按步骤比例分布在 0–75% 区间
          const pos = effectiveTotalSteps > 0
            ? ((i + 1) / effectiveTotalSteps) * RESEARCHER_WEIGHT
            : ((i + 1) / Math.max(completedStepCount, 1)) * RESEARCHER_WEIGHT;
          return (
            <MilestoneDot
              key={`ms-${i}`}
              position={pos}
              title={ms.title}
              completedAt={ms.completedAt}
              compact={compact}
            />
          );
        })}

        {/* 里程碑：报告生成完毕 */}
        {reporterCompletedAt !== null && (
          <MilestoneDot
            position={100}
            title="报告生成完毕"
            completedAt={reporterCompletedAt}
            compact={compact}
            isLast
          />
        )}
      </div>
    </div>
  );
}
