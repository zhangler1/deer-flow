// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

"use client";

import { motion } from "framer-motion";
import {
  Microscope,
  FileSearch,
  Sparkles,
  BookMarked,
} from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";

import { withBasePath } from "~/core/utils/base-path";
import { cn } from "~/lib/utils";

type TabItem = {
  key: string;
  name: string;
  desc: string;
  icon: "microscope" | "filesearch" | "sparkles" | "bookmarked";
  tag?: string;
  type: "image" | "video";
  src: string;
  poster?: string;
};

const ICONS = {
  microscope: Microscope,
  filesearch: FileSearch,
  sparkles: Sparkles,
  bookmarked: BookMarked,
} as const;

// ===== 配置数据：在这里修改 tabs 来添加/修改展示内容 =====
const TABS: TabItem[] = [
  {
    key: "agent",
    name: "深度研究",
    desc: "自主规划、深度分析",
    icon: "microscope",
    tag: "Core",
    type: "video",
    src: withBasePath("/video/tab1.mp4"),
  },
  {
    key: "knowledge",
    name: "资料研究",
    desc: "结合资料进行研究",
    icon: "filesearch",
    tag: "New",
    type: "image",
    src: withBasePath("/images/tab2.png"),
  },
  {
    key: "chat",
    name: "报告编辑",
    desc: "报告在线编辑和下载",
    icon: "sparkles",
    tag: "New",
    type: "video",
    src:  withBasePath("/video/tab3.mp4"),
  },
  {
    key: "quote",
    name: "来源标注",
    desc: "可靠的来源标注",
    tag: "New",
    icon: "bookmarked",
    type: "video",
    src: withBasePath("/video/tab4.mp4"),
  },
];

export function FeatureShowcase({ className }: { className?: string }) {
  const [activeIndex, setActiveIndex] = useState(0);
  const videoRefs = useRef<Map<number, HTMLVideoElement>>(new Map());
  const autoTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // 切换 Tab：仅更新索引，播放/暂停由下方 effect 统一处理
  const handleSwitch = useCallback((nextIndex: number) => {
    setActiveIndex((prev) => (prev === nextIndex ? prev : nextIndex));
  }, []);

  // 每 7s 自动切换 Tab，手动点击（activeIndex 变化）时重置计时
  useEffect(() => {
    if (autoTimerRef.current) clearTimeout(autoTimerRef.current);
    autoTimerRef.current = setTimeout(() => {
      setActiveIndex((prev) => (prev + 1) % TABS.length);
    }, 7_000);
    return () => {
      if (autoTimerRef.current) clearTimeout(autoTimerRef.current);
    };
  }, [activeIndex]);

  // activeIndex 变化时：播放当前视频，暂停其余（并回到开头）
  // 组件首次挂载也会执行一次，自动播放首个视频
  useEffect(() => {
    videoRefs.current.forEach((video, index) => {
      if (index === activeIndex) {
        video.currentTime = 0;
        // preload="none" 的视频在此处首次触发加载
        video.play().catch(() => {});
      } else {
        video.pause();
        video.currentTime = 0;
      }
    });
  }, [activeIndex]);

  // 页面不可见时暂停所有视频，可见时恢复当前视频
  useEffect(() => {
    const handleVisibilityChange = () => {
      if (document.hidden) {
        videoRefs.current.forEach((video) => video.pause());
      } else {
        videoRefs.current.get(activeIndex)?.play().catch(() => {});
      }
    };
    document.addEventListener("visibilitychange", handleVisibilityChange);
    return () =>
      document.removeEventListener("visibilitychange", handleVisibilityChange);
  }, [activeIndex]);

  return (
    <div
      className={cn(
        "flex flex-col sm:flex-row gap-3 w-full p-3 [transform:scale(1.25)] [transform-origin:top_center] mt-4",
        className,
      )}
    >
      {/* 左侧 Tab 列表 */}
      <div className="relative flex sm:flex-col sm:h-full sm:justify-evenly flex-row gap-1 sm:w-48 shrink-0 overflow-x-auto sm:overflow-x-visible  sm:mt-16">
        {/* 灰色竖线背景 */}
        <div className="hidden sm:block absolute left-0 top-0 bottom-0 w-[3px] rounded-full bg-border/60" />
        {TABS.map((tab, index) => {
          const Icon = ICONS[tab.icon];
          const isActive = index === activeIndex;
          return (
            <button
              key={tab.key}
              type="button"
              onClick={() => handleSwitch(index)}
              className={cn(
                "relative flex sm:flex-col sm:items-start flex-row items-center gap-1 rounded-xl pl-4 pr-3 py-3 text-left transition-all duration-200 outline-none",
                "flex-shrink-0 min-w-0 sm:min-w-full",
                isActive
                  ? "bg-[#e8f0fe] text-primary dark:bg-[#1a3050]"
                  : "text-muted-foreground hover:bg-[#f0f4fa] hover:text-foreground dark:hover:bg-[#1e2a3a]",
              )}
            >
              {/* 左侧高亮指示条（选中时蓝色覆盖灰色竖线） */}
              {isActive && (
                <motion.div
                  layoutId="feature-tab-indicator"
                  className="absolute left-0 top-0 bottom-0 h-full w-[3px] rounded-full bg-primary"
                  transition={{ type: "spring", stiffness: 350, damping: 30 }}
                />
              )}
              {/* 标题行：图标 + 名称 + 标签 */}
              <div className="flex items-center gap-2">
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
              </div>
              {/* 描述小字 */}
              <span className="hidden sm:block text-[11px] text-muted-foreground/60 line-clamp-2 leading-tight pl-6">
                {tab.desc}
              </span>
            </button>
          );
        })}
      </div>

      {/* 右侧内容区：一次性渲染所有内容，用 opacity 叠放切换，不用变化的 key */}
      <div className="relative sm:flex-1 sm:basis-0 min-w-0 w-full sm:w-auto min-h-[200px] sm:min-h-[400px] rounded-xl bg-transparent">
        {TABS.map((tab, index) => {
          const isActive = index === activeIndex;
          return (
            <motion.div
              key={tab.key}
              className="absolute inset-0"
              animate={{
                opacity: isActive ? 1 : 0,
                scale: isActive ? 1 : 0.98,
              }}
              transition={{ duration: 0.25, ease: "easeInOut" }}
              style={{
                pointerEvents: isActive ? "auto" : "none",
                zIndex: isActive ? 1 : 0,
              }}
            >
              <div className="flex h-full w-full items-center justify-center p-6">
                <div className="h-full w-full shadow-[6px_8px_12px_-6px_rgba(0,0,0,0.3)] rounded-lg overflow-hidden">
                  {tab.type === "video" ? (
                    <video
                      ref={(el) => {
                        if (el) videoRefs.current.set(index, el);
                        else videoRefs.current.delete(index);
                      }}
                      src={tab.src}
                      poster={tab.poster}
                      loop
                      muted
                      playsInline
                      preload={isActive ? "auto" : "none"}
                      className="h-full w-full object-contain"
                    />
                  ) : (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img
                      src={tab.src}
                      alt={tab.name}
                      className="h-full w-full object-contain"
                    />
                  )}
                </div>
              </div>
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}
