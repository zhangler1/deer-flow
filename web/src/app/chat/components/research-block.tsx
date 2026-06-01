// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

import { Check, Copy, Pencil, Undo2, X, Download, Loader2, FileText, FileDown, ChevronsDownUp, ChevronsUpDown } from "lucide-react";
import { useTranslations } from "next-intl";
import { useCallback, useEffect, useState } from "react";

import { ScrollContainer } from "~/components/deer-flow/scroll-container";
import { Tooltip } from "~/components/deer-flow/tooltip";
import { Button } from "~/components/ui/button";
import { Card } from "~/components/ui/card";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "~/components/ui/dropdown-menu";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "~/components/ui/tabs";
import { resolveServiceURL } from "~/core/api/resolve-service-url";
import { useReplay } from "~/core/replay";
import { closeResearch, useStore } from "~/core/store";
import { cn } from "~/lib/utils";

import { ResearchActivitiesBlock } from "./research-activities-block";
import { ResearchReportBlock } from "./research-report-block";

export function ResearchBlock({
  className,
  researchId = null,
}: {
  className?: string;
  researchId: string | null;
}) {
  const t = useTranslations("chat.research");
  const reportId = useStore((state) =>
    researchId ? state.researchReportIds.get(researchId) : undefined,
  );
  const [activeTab, setActiveTab] = useState("activities");
  const hasReport = useStore((state) =>
    researchId ? state.researchReportIds.has(researchId) : false,
  );
  const reportStreaming = useStore((state) =>
    reportId ? (state.messages.get(reportId)?.isStreaming ?? false) : false,
  );
  // 当前研究是否正在进行中（用于判断点击“报告”时的提示文案）
  const researchOngoing = useStore(
    (state) => !!researchId && state.ongoingResearchId === researchId,
  );
  const { isReplay } = useReplay();
  useEffect(() => {
    if (hasReport) {
      setActiveTab("report");
    }
  }, [hasReport]);

  const [editing, setEditing] = useState(false);
  const [sectionsExpanded, setSectionsExpanded] = useState(false);
  const [copied, setCopied] = useState(false);
  const handleCopy = useCallback(() => {
    if (!reportId) {
      return;
    }
    const report = useStore.getState().messages.get(reportId);
    if (!report) {
      return;
    }
    
    // 降级方案：兼容非 HTTPS 环境
    if (navigator.clipboard?.writeText) {
      // 使用现代 Clipboard API
      void navigator.clipboard.writeText(report.content);
    } else {
      // 降级方案：使用传统的 execCommand 方法
      const textArea = document.createElement('textarea');
      textArea.value = report.content;
      textArea.style.position = 'fixed';
      textArea.style.left = '-999999px';
      textArea.style.top = '-999999px';
      document.body.appendChild(textArea);
      textArea.focus();
      textArea.select();
      try {
        document.execCommand('copy');
      } catch (err) {
        console.error('[handleCopy] 复制失败:', err);
      } finally {
        document.body.removeChild(textArea);
      }
    }
    
    setCopied(true);
    setTimeout(() => {
      setCopied(false);
    }, 1000);
  }, [reportId]);

  const [downloading, setDownloading] = useState(false);

  // Download report in specified format
  const handleDownload = useCallback(async (format: 'docx' | 'markdown') => {
    if (!reportId) {
      return;
    }
    const report = useStore.getState().messages.get(reportId);
    if (!report) {
      return;
    }
    const now = new Date();
    const pad = (n: number) => n.toString().padStart(2, '0');
    const timestamp = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}_${pad(now.getHours())}-${pad(now.getMinutes())}-${pad(now.getSeconds())}`;
    const filename = `research-report-${timestamp}`;

    if (format === 'markdown') {
      // 直接下载 Markdown
      const blob = new Blob([report.content], { type: 'text/markdown' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${filename}.md`;
      document.body.appendChild(a);
      a.click();
      setTimeout(() => {
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
      }, 0);
      return;
    }

    // 调用后端接口转换为 Word（后端通过 nginx 负载均衡转发到 easyparse）
    try {
      setDownloading(true);
      const res = await fetch(resolveServiceURL("markdown/to_word"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content: report.content, filename }),
      });

      if (res.ok) {
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${filename}.docx`;
        document.body.appendChild(a);
        a.click();
        setTimeout(() => {
          document.body.removeChild(a);
          URL.revokeObjectURL(url);
        }, 0);
        return;
      }

      // API 返回错误，降级为 Markdown 下载
      console.warn(`[handleDownload] Word 转换失败 (status=${res.status})，降级下载 Markdown`);
    } catch (err) {
      // 网络异常（easyparse 服务不可达等），降级为 Markdown 下载
      console.warn('[handleDownload] Word 转换请求异常，降级下载 Markdown:', err);
    } finally {
      setDownloading(false);
    }

    // 降级：下载原始 Markdown
    const blob = new Blob([report.content], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${filename}.md`;
    document.body.appendChild(a);
    a.click();
    setTimeout(() => {
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    }, 0);
  }, [reportId]);

    
  const handleEdit = useCallback(() => {
    setEditing((editing) => !editing);
  }, []);

  // When the research id changes, set the active tab to activities
  useEffect(() => {
    if (!hasReport) {
      setActiveTab("activities");
    }
  }, [hasReport, researchId]);

  return (
    <div className={cn("h-full w-full", className)}>
      <Card className={cn("relative h-full w-full pt-4", className)}>
        <div className="absolute right-4 flex h-9 items-center justify-center">
          {hasReport && !reportStreaming && (
            <>
              <Tooltip title={sectionsExpanded ? "折叠全部" : "展开全部"}>
                <Button
                  className="text-gray-400"
                  size="icon"
                  variant="ghost"
                  onClick={() => setSectionsExpanded((v) => !v)}
                >
                  {sectionsExpanded ? <ChevronsDownUp /> : <ChevronsUpDown />}
                </Button>
              </Tooltip>
              <Tooltip title={t("edit")}>
                <Button
                  className="text-gray-400"
                  size="icon"
                  variant="ghost"
                  disabled={isReplay}
                  onClick={handleEdit}
                >
                  {editing ? <Undo2 /> : <Pencil />}
                </Button>
              </Tooltip>
              <Tooltip title={t("copy")}>
                <Button
                  className="text-gray-400"
                  size="icon"
                  variant="ghost"
                  onClick={handleCopy}
                >
                  {copied ? <Check /> : <Copy />}
                </Button>
              </Tooltip>
              <DropdownMenu>
                <Tooltip title={t("downloadReport")}>
                  <DropdownMenuTrigger asChild>
                    <Button
                      className="text-gray-400"
                      size="icon"
                      variant="ghost"
                      disabled={downloading}
                    >
                      {downloading ? <Loader2 className="animate-spin" /> : <Download />}
                    </Button>
                  </DropdownMenuTrigger>
                </Tooltip>
                <DropdownMenuContent align="end" className="min-w-[140px]">
                  <DropdownMenuItem
                    className="flex items-center gap-2 cursor-pointer"
                    onClick={() => handleDownload('docx')}
                  >
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                      <path d="M3.28338 2.41963C3 2.9758 3 3.70386 3 5.16V18.84C3 20.2961 3 21.0242 3.28338 21.5804C3.53265 22.0696 3.9304 22.4673 4.41962 22.7166C4.9758 23 5.70386 23 7.16 23H16.84C18.2961 23 19.0242 23 19.5804 22.7166C20.0696 22.4673 20.4673 22.0696 20.7166 21.5804C21 21.0242 21 20.2961 21 18.84V7L15 1H7.16C5.70386 1 4.9758 1 4.41962 1.28338C3.9304 1.53265 3.53265 1.9304 3.28338 2.41963Z" fill="url(#word_grad)"/>
                      <path d="M15 1L21 7H19.16C17.7039 7 16.9758 7 16.4196 6.71662C15.9304 6.46735 15.5327 6.0696 15.2834 5.58038C15 5.0242 15 4.29614 15 2.84V1Z" fill="white" fillOpacity="0.55"/>
                      <path d="M7.51521 9.17188C7.47819 9.17188 7.44134 9.17699 7.40571 9.18708C7.19219 9.24756 7.06812 9.46968 7.12859 9.6832L9.12813 16.7432C9.17711 16.9161 9.33499 17.0355 9.51475 17.0355H10.3832C10.5648 17.0355 10.7238 16.9138 10.7711 16.7385L12.0036 12.1778L13.2283 16.7379C13.2755 16.9135 13.4346 17.0355 13.6164 17.0355H14.4848C14.6646 17.0355 14.8225 16.9161 14.8715 16.7432L16.871 9.6832C16.8811 9.64758 16.8862 9.61073 16.8862 9.5737C16.8862 9.35178 16.7063 9.17188 16.4844 9.17188H15.6134C15.4302 9.17188 15.2702 9.29577 15.2244 9.47312L14.0401 14.0536L12.8173 9.47012C12.7704 9.29424 12.6111 9.17188 12.429 9.17188H11.5803C11.3985 9.17188 11.2394 9.29394 11.1922 9.46953L9.9606 14.0578L8.77522 9.47312C8.72937 9.29577 8.56937 9.17188 8.38619 9.17188H7.51521Z" fill="#19205A"/>
                      <defs><linearGradient id="word_grad" x1="21" y1="23" x2="-0.443772" y2="18.8668" gradientUnits="userSpaceOnUse"><stop stopColor="#44ADFE"/><stop offset="1" stopColor="#5580FF"/></linearGradient></defs>
                    </svg>
                    <span>Word</span>
                  </DropdownMenuItem>
                  <DropdownMenuItem
                    className="flex items-center gap-2 cursor-pointer"
                    onClick={() => handleDownload('markdown')}
                  >
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                      <path d="M3.28338 2.41963C3 2.9758 3 3.70386 3 5.16V18.84C3 20.2961 3 21.0242 3.28338 21.5804C3.53265 22.0696 3.9304 22.4673 4.41962 22.7166C4.9758 23 5.70386 23 7.16 23H16.84C18.2961 23 19.0242 23 19.5804 22.7166C20.0696 22.4673 20.4673 22.0696 20.7166 21.5804C21 21.0242 21 20.2961 21 18.84V7L15 1H7.16C5.70386 1 4.9758 1 4.41962 1.28338C3.9304 1.53265 3.53265 1.9304 3.28338 2.41963Z" fill="url(#md_grad)" fillOpacity="0.3"/>
                      <path d="M8.24793 17.9866L9.33986 16.9158H16.4568C16.6046 16.9158 16.7321 16.9701 16.8393 17.0788C16.9464 17.1839 17 17.309 17 17.4539C17 17.6025 16.9464 17.7275 16.8393 17.829C16.7321 17.9341 16.6046 17.9866 16.4568 17.9866H8.24793ZM7.62714 17.4811L6.28579 17.9866C6.20449 18.0156 6.13059 17.9975 6.06407 17.9323C6.00126 17.867 5.98463 17.7927 6.01419 17.7094L6.55738 16.432L12.793 10.3222L13.8572 11.3713L7.62714 17.4811ZM14.3893 10.8603L13.314 9.81119L13.9127 9.22956C14.0605 9.08823 14.2138 9.01213 14.3727 9.00125C14.5316 8.99038 14.6794 9.05018 14.8161 9.18064L15.0323 9.39807C15.169 9.53215 15.2337 9.67529 15.2263 9.82749C15.2189 9.9797 15.1395 10.1301 14.988 10.2787L14.3893 10.8603Z" fill="#003294"/>
                      <path d="M15 1L21 7H19.16C17.7039 7 16.9758 7 16.4196 6.71662C15.9304 6.46735 15.5327 6.0696 15.2834 5.58038C15 5.0242 15 4.29614 15 2.84V1Z" fill="white" fillOpacity="0.55"/>
                      <defs><linearGradient id="md_grad" x1="22.4318" y1="19.5" x2="1.13653" y2="9.04595" gradientUnits="userSpaceOnUse"><stop offset="0.25" stopColor="#75A4FF"/><stop offset="1" stopColor="#0057FF"/></linearGradient></defs>
                    </svg>
                    <span>Markdown</span>
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </>
          )}
          <Tooltip title={t("close")}>
            <Button
              className="text-gray-400"
              size="sm"
              variant="ghost"
              onClick={() => {
                closeResearch();
              }}
            >
              <X />
            </Button>
          </Tooltip>
        </div>
        <Tabs
          className="flex h-full w-full flex-col"
          value={activeTab}
          onValueChange={(value) => setActiveTab(value)}
        >
          <div className="flex w-full justify-center">
            <TabsList className="">
              {/* 报告未就绪时：disabled + 悬停 Tooltip 提示；外层 span 捕获 hover */}
              {!hasReport ? (
                <Tooltip
                  title={
                    researchOngoing
                      ? "报告正在生成中，请稍候……"
                      : "暂无报告"
                  }
                >
                  <span className="inline-flex">
                    <TabsTrigger
                      className="px-8"
                      value="report"
                      disabled
                    >
                      {t("report")}
                    </TabsTrigger>
                  </span>
                </Tooltip>
              ) : (
                <TabsTrigger className="px-8" value="report">
                  {t("report")}
                </TabsTrigger>
              )}
              <TabsTrigger className="px-8" value="activities">
                {t("activities")}
              </TabsTrigger>
            </TabsList>
          </div>
          <TabsContent
            className="h-full min-h-0 flex-grow px-8"
            value="report"
            forceMount
            hidden={activeTab !== "report"}
          >
            <ScrollContainer
              className="px-5pb-20 h-full"
              scrollShadowColor="var(--card)"
              autoScrollToBottom={!hasReport || reportStreaming}
            >
              {reportId && researchId && (
                <ResearchReportBlock
                  className="mt-4"
                  researchId={researchId}
                  messageId={reportId}
                  editing={editing}
                  allExpanded={sectionsExpanded}
                />
              )}
            </ScrollContainer>
          </TabsContent>
          <TabsContent
            className="h-full min-h-0 flex-grow px-8"
            value="activities"
            forceMount
            hidden={activeTab !== "activities"}
          >
            <ScrollContainer
              className="h-full"
              scrollShadowColor="var(--card)"
              autoScrollToBottom={!hasReport || reportStreaming}
            >
              {researchId && (
                <ResearchActivitiesBlock
                  className="mt-4"
                  researchId={researchId}
                />
              )}
            </ScrollContainer>
          </TabsContent>
        </Tabs>
      </Card>
    </div>
  );
}
