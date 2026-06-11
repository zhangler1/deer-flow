// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

"use client";

import { motion, AnimatePresence } from "framer-motion";
import {
  Microscope,
  FileSearch,
  Sparkles,
  BookMarked,
  Image as ImageIcon,
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
    desc: "基于多 Agent 协作，集成行内外知识检索，自主规划搜索、生成研究报告。",
    icon: "microscope",
    tag: "Core",
    type: "video",
    src: withBasePath("/video/tab1.mp4"),
  },
  {
    key: "knowledge",
    name: "资料研究",
    desc: "支持上传pdf，docx，ppt，xlsx，csv，txt，md等格式文件（禁止上传涉密资料）",
    icon: "filesearch",
    tag: "New",
    type: "image",
    src: withBasePath("/images/tab2.png"),
  },
  {
    key: "chat",
    name: "报告编辑",
    desc: "自动生成专业 Markdown 格式研究报告，支持线编辑和下载。",
    icon: "sparkles",
    tag: "New",
    type: "video",
    src:  withBasePath("/video/tab3.mp4"),
  },
  {
    key: "quote",
    name: "来源标注",
    desc: "可靠的来源标注，支持点击查看原文，行内支持跳转交行知道链接。",
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

  // 切换 Tab 时控制视频播放/暂停
  const handleSwitch = useCallback(
    (nextIndex: number) => {
      if (nextIndex === activeIndex) return;
      // 停止上一个视频（暂停并回到开头）
      const prevTab = TABS[activeIndex];
      if (prevTab?.type === "video") {
        const prevVideo = videoRefs.current.get(activeIndex);
        if (prevVideo) {
          prevVideo.pause();
          prevVideo.currentTime = 0;
        }
      }
      // 播放下一个视频
      const nextTab = TABS[nextIndex];
      if (nextTab?.type === "video") {
        const nextVideo = videoRefs.current.get(nextIndex);
        if (nextVideo) {
          nextVideo.currentTime = 0;
          nextVideo.play().catch(() => {});
        }
      }
      setActiveIndex(nextIndex);
    },
    [activeIndex],
  );

  // 每 10s 自动切换 Tab，手动点击时重置计时
  useEffect(() => {
    if (autoTimerRef.current) clearTimeout(autoTimerRef.current);
    autoTimerRef.current = setTimeout(() => {
      const next = (activeIndex + 1) % TABS.length;
      handleSwitch(next);
    }, 7_000);
    return () => {
      if (autoTimerRef.current) clearTimeout(autoTimerRef.current);
    };
  }, [activeIndex, handleSwitch]);

  // 组件挂载后自动播放首个视频（如果有）
  useEffect(() => {
    const firstTab = TABS[0];
    if (firstTab?.type === "video") {
      const firstVideo = videoRefs.current.get(0);
      if (firstVideo) firstVideo.play().catch(() => {});
    }
  }, []);

  // 页面不可见时暂停所有视频，可见时恢复当前视频
  useEffect(() => {
    const handleVisibilityChange = () => {
      if (document.hidden) {
        videoRefs.current.forEach((video) => video.pause());
      } else {
        const activeTab = TABS[activeIndex];
        if (activeTab?.type === "video") {
          const activeVideo = videoRefs.current.get(activeIndex);
          if (activeVideo) activeVideo.play().catch(() => {});
        }
      }
    };
    document.addEventListener("visibilitychange", handleVisibilityChange);
    return () => document.removeEventListener("visibilitychange", handleVisibilityChange);
  }, [activeIndex]);

  return (
    <div
      className={cn(
        "flex flex-col sm:flex-row gap-3 w-full p-3",
        className,
      )}
    >
      {/* 左侧 Tab 列表 */}
      <div className="relative flex sm:flex-col flex-row gap-1 sm:w-48 shrink-0 overflow-x-auto sm:overflow-x-visible">
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
                  ? "bg-primary/10 text-primary"
                  : "text-muted-foreground hover:bg-muted/60 hover:text-foreground",
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

      {/* 右侧内容区 */}
      <div className="relative sm:flex-1 sm:basis-0 min-w-0 w-full sm:w-auto min-h-[200px] sm:min-h-[400px] rounded-xl bg-transparent">
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
                  <div className="flex h-full w-full items-center justify-center p-6">
                    <div className="h-full w-full shadow-[6px_8px_12px_-6px_rgba(0,0,0,0.3)] rounded-lg overflow-hidden">
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
                        className="h-full w-full object-contain"
                      />
                    </div>
                  </div>
                );
              }
              return (
                <div className="flex h-full w-full items-center justify-center p-6">
                  <div className="h-full w-full shadow-[6px_8px_12px_-6px_rgba(0,0,0,0.3)] rounded-lg overflow-hidden">
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img
                      src={tab.src}
                      alt={tab.name}
                      className="h-full w-full object-contain"
                    />
                  </div>
                </div>
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
