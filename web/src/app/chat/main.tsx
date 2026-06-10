// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { useStore } from "~/core/store";
import { cn } from "~/lib/utils";

import { MessagesBlock } from "./components/messages-block";
import { ResearchBlock } from "./components/research-block";

// 默认左侧占比 40%
const DEFAULT_LEFT_RATIO = 0.40;
// 左侧最小宽度（像素）
const MIN_LEFT_WIDTH = 400;
// 右侧最小占比
const MIN_RIGHT_RATIO = 0.45;

export default function Main() {
  const openResearchId = useStore((state) => state.openResearchId);
  const doubleColumnMode = useMemo(
    () => openResearchId !== null,
    [openResearchId],
  );

  const containerRef = useRef<HTMLDivElement>(null);
  const [leftRatio, setLeftRatio] = useState(DEFAULT_LEFT_RATIO);
  const [isDraggingState, setIsDraggingState] = useState(false);
  const isDragging = useRef(false);

  const handleMouseDown = useCallback(() => {
    isDragging.current = true;
    setIsDraggingState(true);
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
  }, []);

  const handleMouseUp = useCallback(() => {
    isDragging.current = false;
    setIsDraggingState(false);
    document.body.style.cursor = "";
    document.body.style.userSelect = "";
  }, []);

  const handleMouseMove = useCallback((e: MouseEvent) => {
    if (!isDragging.current || !containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    const containerWidth = rect.width;
    const newLeftWidth = e.clientX - rect.left;
    const newRatio = newLeftWidth / containerWidth;

    // 限制比例范围，确保右侧不小于最小占比，左侧不小于最小宽度
    const minRatio = MIN_LEFT_WIDTH / containerWidth;
    const maxRatio = Math.max(minRatio, 1 - MIN_RIGHT_RATIO);
    const clampedRatio = Math.max(minRatio, Math.min(maxRatio, newRatio));
    setLeftRatio(clampedRatio);
  }, []);

  useEffect(() => {
    window.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("mouseup", handleMouseUp);
    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", handleMouseUp);
    };
  }, [handleMouseMove, handleMouseUp]);

  // 同步 leftRatio 到 CSS 变量，让 header 渐变跟随分隔条
  useEffect(() => {
    const root = document.querySelector<HTMLElement>(".overscroll-none");
    if (!root) return;

    const updateSplit = () => {
      if (doubleColumnMode && containerRef.current) {
        const containerWidth = containerRef.current.getBoundingClientRect().width;
        const splitPx = leftRatio * (containerWidth - 32); // 减去 px-4 = 32px
        root.style.setProperty("--header-split", `${splitPx}px`);
      } else {
        root.style.setProperty("--header-split", "0px");
      }
    };

    updateSplit();
    window.addEventListener("resize", updateSplit);
    return () => {
      window.removeEventListener("resize", updateSplit);
      root.style.removeProperty("--header-split");
    };
  }, [leftRatio, doubleColumnMode]);

  // 拖动分隔条时保持左侧消息列表沉底
  useEffect(() => {
    if (!doubleColumnMode || !containerRef.current) return;
    const leftViewport = containerRef.current.querySelector(
      "[data-radix-scroll-area-viewport]",
    ) as HTMLElement | null;
    if (leftViewport) {
      leftViewport.scrollTop = leftViewport.scrollHeight;
    }
  }, [leftRatio, doubleColumnMode]);

  return (
    <div
      ref={containerRef}
      className="flex h-full w-full justify-center-safe px-4 pt-12 pb-4"
    >
      {doubleColumnMode ? (
        <>
          {/* 左侧：计划策略 / 消息列表 */}
          <div
            className={cn(
              "shrink-0 bg-gray-50/60",
              !isDraggingState && "transition-all duration-300 ease-out",
            )}
            style={{ width: `${leftRatio * 100}%` }}
          >
            <MessagesBlock className="h-full w-full" />
          </div>

          {/* 拖动分隔条 - w-0 不占宽度，灰白紧贴 */}
          <div
            className="relative w-0 shrink-0"
            style={{ zIndex: 50 }}
          >
            {/* 细线 - 贯穿整个视口，粗一倍 */}
            <div
              className="absolute left-1/2 -top-12 w-0.5 -translate-x-1/2 bg-gradient-to-b from-transparent via-border to-transparent opacity-0 transition-opacity hover:opacity-100"
              style={{ height: "calc(100% + 3rem)" }}
            />
            {/* 可点击热区：仅放在分隔条右侧（报告面板边缘），避免遮挡左侧 MessagesBlock 的滚动条 */}
            <div
              className="absolute top-0 left-0 h-full w-8 cursor-col-resize group"
              onMouseDown={handleMouseDown}
            >
              {/* 热区内细线（视觉居中） */}
              <div className="absolute right-full top-0 h-full w-0.5 bg-gradient-to-b from-transparent via-border to-transparent opacity-0 transition-opacity group-hover:opacity-100" />
              {/* 抓手（视觉居中） */}
              <div className="absolute right-full top-1/2 flex h-14 w-3.5 translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-full border border-solid border-border bg-white shadow-sm opacity-0 transition-opacity group-hover:opacity-100">
                <div className="h-5 w-px rounded-full bg-muted-foreground/30" />
              </div>
            </div>
          </div>

          {/* 右侧：报告生成 */}
          <div
            className={cn(
              "h-full min-w-0 overflow-hidden bg-white",
              !isDraggingState && "transition-all duration-300 ease-out",
            )}
            style={{
              width: `${(1 - leftRatio) * 100}%`,
              boxShadow: "-8px 0 24px -12px rgba(0, 0, 0, 0.06)",
            }}
          >
            <ResearchBlock className="rounded-tl-none rounded-tr-none" researchId={openResearchId} />
          </div>
        </>
      ) : (
        <>
          <MessagesBlock
            className={cn(
              "flex-1 min-w-0 transition-all duration-300 ease-out",
            )}
          />
          <ResearchBlock
            className={cn(
              "w-0 shrink-0 overflow-hidden pb-4 transition-all duration-300 ease-out",
              "scale-0",
            )}
            researchId={openResearchId}
          />
        </>
      )}
    </div>
  );
}
