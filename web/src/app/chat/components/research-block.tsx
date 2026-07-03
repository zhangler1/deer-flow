// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

import { Check, Copy, Pencil, Undo2, X, Download, Loader2, FileText, FileDown, ChevronsDownUp, ChevronsUpDown } from "lucide-react";
import { useTranslations } from "next-intl";
import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

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
import { closeResearch, useStore, REPORT_CHAT_PLACEHOLDER_ID } from "~/core/store";
import { stripThinkTags } from "~/core/utils/think-tag-parser";
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
  // 占位符状态：直连 LLM 对话已开启右侧面板，但尚未收到 reporter 消息
  const isPlaceholder = researchId === REPORT_CHAT_PLACEHOLDER_ID;

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
    // 过滤 think tag 后再复制
    const cleanContent = stripThinkTags(report.content);
    if (navigator.clipboard?.writeText) {
      // 使用现代 Clipboard API
      void navigator.clipboard.writeText(cleanContent);
    } else {
      // 降级方案：使用传统的 execCommand 方法
      const textArea = document.createElement('textarea');
      textArea.value = cleanContent;
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

  // Download report as encrypted Word document
  const handleDownload = useCallback(async () => {
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

    // 过滤 think tag 后再下载
    const cleanContent = stripThinkTags(report.content);

    // 调用后端接口转换为加密 Word 文档
    try {
      setDownloading(true);
      const res = await fetch(resolveServiceURL("markdown/to_word/encrypted"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content: cleanContent, filename }),
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

      // 文档转换失败
      console.warn(`[handleDownload] Word 转换失败 (status=${res.status})`);
      toast.error("文档下载失败，请稍后重试");
    } catch (err) {
      // 网络异常
      console.warn('[handleDownload] Word 转换请求异常:', err);
      toast.error("网络异常，下载失败");
    } finally {
      setDownloading(false);
    }
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
          {/* 占位符状态下不显示工具栏按钮（仅保留关闭） */}
          {!isPlaceholder && hasReport && !reportStreaming && (
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
                    onClick={() => handleDownload()}
                  >
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                      <path d="M3.28338 2.41963C3 2.9758 3 3.70386 3 5.16V18.84C3 20.2961 3 21.0242 3.28338 21.5804C3.53265 22.0696 3.9304 22.4673 4.41962 22.7166C4.9758 23 5.70386 23 7.16 23H16.84C18.2961 23 19.0242 23 19.5804 22.7166C20.0696 22.4673 20.4673 22.0696 20.7166 21.5804C21 21.0242 21 20.2961 21 18.84V7L15 1H7.16C5.70386 1 4.9758 1 4.41962 1.28338C3.9304 1.53265 3.53265 1.9304 3.28338 2.41963Z" fill="url(#word_grad)"/>
                      <path d="M15 1L21 7H19.16C17.7039 7 16.9758 7 16.4196 6.71662C15.9304 6.46735 15.5327 6.0696 15.2834 5.58038C15 5.0242 15 4.29614 15 2.84V1Z" fill="white" fillOpacity="0.55"/>
                      <path d="M7.51521 9.17188C7.47819 9.17188 7.44134 9.17699 7.40571 9.18708C7.19219 9.24756 7.06812 9.46968 7.12859 9.6832L9.12813 16.7432C9.17711 16.9161 9.33499 17.0355 9.51475 17.0355H10.3832C10.5648 17.0355 10.7238 16.9138 10.7711 16.7385L12.0036 12.1778L13.2283 16.7379C13.2755 16.9135 13.4346 17.0355 13.6164 17.0355H14.4848C14.6646 17.0355 14.8225 16.9161 14.8715 16.7432L16.871 9.6832C16.8811 9.64758 16.8862 9.61073 16.8862 9.5737C16.8862 9.35178 16.7063 9.17188 16.4844 9.17188H15.6134C15.4302 9.17188 15.2702 9.29577 15.2244 9.47312L14.0401 14.0536L12.8173 9.47012C12.7704 9.29424 12.6111 9.17188 12.429 9.17188H11.5803C11.3985 9.17188 11.2394 9.29394 11.1922 9.46953L9.9606 14.0578L8.77522 9.47312C8.72937 9.29577 8.56937 9.17188 8.38619 9.17188H7.51521Z" fill="#19205A"/>
                      <defs><linearGradient id="word_grad" x1="21" y1="23" x2="-0.443772" y2="18.8668" gradientUnits="userSpaceOnUse"><stop stopColor="#44ADFE"/><stop offset="1" stopColor="#5580FF"/></linearGradient></defs>
                    </svg>
                    <span>Word</span>
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
        {isPlaceholder ? (
          /* 占位符状态：等待用户提问 */
          <div className="flex h-full w-full flex-col items-center justify-center gap-3 text-muted-foreground">
            <FileText className="h-10 w-10 opacity-30" />
            <p className="text-sm">已准备就绪，请在左侧输入问题</p>
          </div>
        ) : (
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
              className="px-5 pb-20 h-full"
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
        )}
      </Card>
    </div>
  );
}
