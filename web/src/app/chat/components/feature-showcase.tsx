// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

"use client";

import { motion, AnimatePresence } from "framer-motion";
import {
  BrainCircuit,
  Database,
  MessageSquareCode,
  ArrowRightCircle,
  Image as ImageIcon,
} from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";

import { cn } from "~/lib/utils";

type TabItem = {
  key: string;
  name: string;
  desc: string;
  icon: "brain" | "database" | "chat" | "arrow";
  tag?: string;
  type: "image" | "video";
  src: string;
  poster?: string;
};

const ICONS = {
  brain: BrainCircuit,
  database: Database,
  chat: MessageSquareCode,
  arrow: ArrowRightCircle,
} as const;

// ===== 配置数据：在这里修改 tabs 来添加/修改展示内容 =====
const TABS: TabItem[] = [
  {
    key: "agent",
    name: "深度研究",
    desc: "基于多 Agent 协作，自动规划、搜索、分析并生成结构化报告。",
    icon: "brain",
    tag: "Core",
    type: "image",
    src: "https://img.alicdn.com/imgextra/i4/O1CN01DNLwq91Oi3TnQtUfM_!!6000000001738-0-tps-3080-2184.jpg",
  },
  {
    key: "knowledge",
    name: "智能搜索",
    desc: "集成多种搜索引擎，智能抓取和解析网页内容，精准信息检索。",
    icon: "database",
    tag: "New",
    type: "video",
    src: "https://cloud.video.taobao.com/vod/Dk1X5H_Z_liQf2rGkCYDfm1nZgID09FgdnfTvowFPBg.mp4",
  },
  {
    key: "chat",
    name: "报告生成",
    desc: "自动生成专业 Markdown 格式研究报告，支持多种风格与模板。",
    icon: "chat",
    type: "image",
    src: "https://img.alicdn.com/imgextra/i4/O1CN01DNLwq91Oi3TnQtUfM_!!6000000001738-0-tps-3080-2184.jpg",
  },
  {
    key: "workflow",
    name: "工作流编排",
    desc: "灵活的工作流编排引擎，支持自定义节点和流程控制。",
    icon: "arrow",
    type: "image",
    src: "https://img.alicdn.com/imgextra/i4/O1CN01DNLwq91Oi3TnQtUfM_!!6000000001738-0-tps-3080-2184.jpg",
  },
];

export function FeatureShowcase({ className }: { className?: string }) {
  const [activeIndex, setActiveIndex] = useState(0);
  const videoRefs = useRef<Map<number, HTMLVideoElement>>(new Map());

  // 切换 Tab 时控制视频播放/暂停
  const handleSwitch = useCallback(
    (nextIndex: number) => {
      if (nextIndex === activeIndex) return;
      // 暂停上一个视频
      const prevTab = TABS[activeIndex];
      if (prevTab?.type === "video") {
        const prevVideo = videoRefs.current.get(activeIndex);
        if (prevVideo) prevVideo.pause();
      }
      // 播放下一个视频
      const nextTab = TABS[nextIndex];
      if (nextTab?.type === "video") {
        const nextVideo = videoRefs.current.get(nextIndex);
        if (nextVideo) {
          nextVideo.currentTime = 0;
          void nextVideo.play();
        }
      }
      setActiveIndex(nextIndex);
    },
    [activeIndex],
  );

  // 组件挂载后自动播放首个视频（如果有）
  useEffect(() => {
    const firstTab = TABS[0];
    if (firstTab?.type === "video") {
      const firstVideo = videoRefs.current.get(0);
      if (firstVideo) void firstVideo.play();
    }
  }, []);

  return (
    <div
      className={cn(
        "flex flex-col sm:flex-row gap-3 w-full rounded-2xl border border-border/60 bg-card/80 p-3 shadow-sm backdrop-blur-sm",
        className,
      )}
    >
      {/* 左侧 Tab 列表 */}
      <div className="flex sm:flex-col flex-row gap-1 sm:w-40 shrink-0 overflow-x-auto sm:overflow-x-visible">
        {TABS.map((tab, index) => {
          const Icon = ICONS[tab.icon];
          const isActive = index === activeIndex;
          return (
            <button
              key={tab.key}
              type="button"
              onClick={() => handleSwitch(index)}
              className={cn(
                "relative flex items-center gap-2 rounded-xl px-3 py-2.5 text-left transition-all duration-200 outline-none",
                "flex-shrink-0 min-w-0 sm:min-w-full",
                isActive
                  ? "bg-primary/10 text-primary"
                  : "text-muted-foreground hover:bg-muted/60 hover:text-foreground",
              )}
            >
              {/* 左侧高亮指示条 */}
              {isActive && (
                <motion.div
                  layoutId="feature-tab-indicator"
                  className="absolute left-0 top-1/2 -translate-y-1/2 h-5 w-[3px] rounded-full bg-primary"
                  transition={{ type: "spring", stiffness: 350, damping: 30 }}
                />
              )}
              <Icon
                size={16}
                className={cn(
                  "shrink-0 transition-colors",
                  isActive ? "text-primary" : "text-muted-foreground/70",
                )}
              />
              <span className="text-sm font-medium whitespace-nowrap truncate">
                {tab.name}
              </span>
              {tab.tag && (
                <span
                  className={cn(
                    "shrink-0 rounded px-1 py-px text-[10px] font-semibold uppercase leading-tight",
                    tab.tag === "New"
                      ? "bg-emerald-500/10 text-emerald-600"
                      : "bg-blue-500/10 text-blue-600",
                  )}
                >
                  {tab.tag}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* 右侧内容区 */}
      <div className="relative sm:flex-1 sm:basis-0 min-w-0 w-full sm:w-auto min-h-[200px] sm:min-h-[280px] rounded-xl overflow-hidden bg-muted/40">
        {/* Tab 描述 */}
        <div className="absolute top-2 left-3 right-3 z-10 pointer-events-none">
          <p className="text-xs text-muted-foreground/80 line-clamp-2 drop-shadow-sm">
            {TABS[activeIndex]?.desc}
          </p>
        </div>

        {/* 内容切换 */}
        <AnimatePresence mode="wait">
          <motion.div
            key={activeIndex}
            className="absolute inset-0"
            initial={{ opacity: 0, scale: 0.98 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 1.02 }}
            transition={{ duration: 0.25, ease: "easeInOut" }}
          >
            {(() => {
              const tab = TABS[activeIndex];
              if (!tab) return null;
              if (tab.type === "video") {
                return (
                  <video
                    key={`video-${activeIndex}`}
                    ref={(el) => {
                      if (el) videoRefs.current.set(activeIndex, el);
                      else videoRefs.current.delete(activeIndex);
                    }}
                    src={tab.src}
                    poster={tab.poster}
                    autoPlay
                    loop
                    muted
                    playsInline
                    className="h-full w-full object-cover"
                  />
                );
              }
              return (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={tab.src}
                  alt={tab.name}
                  className="h-full w-full object-cover"
                />
              );
            })()}
          </motion.div>
        </AnimatePresence>

        {/* 空状态兜底 */}
        {!TABS[activeIndex] && (
          <div className="flex h-full w-full items-center justify-center text-muted-foreground/50">
            <ImageIcon size={32} />
          </div>
        )}
      </div>
    </div>
  );
}
