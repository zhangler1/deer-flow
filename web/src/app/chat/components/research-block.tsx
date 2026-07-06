// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

import { Check, Copy, Pencil, Undo2, X, Download, Loader2, FileText, ChevronsDownUp, ChevronsUpDown } from "lucide-react";
import { useTranslations } from "next-intl";
import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { ScrollContainer } from "~/components/deer-flow/scroll-container";
import { Tooltip } from "~/components/deer-flow/tooltip";
import { Button } from "~/components/ui/button";
import { Card } from "~/components/ui/card";
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
        const disposition = res.headers.get('Content-Disposition');
        const serverFilename = disposition?.split('filename=')[1]?.trim()?.replace(/"/g, '');
        a.download = serverFilename || `${filename}.docx`;
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
              <Tooltip title={t("downloadReport")}>
                <Button
                  className="text-gray-400"
                  size="icon"
                  variant="ghost"
                  disabled={downloading}
                  onClick={() => handleDownload()}
                >
                  {downloading ? <Loader2 className="animate-spin" /> : <Download />}
                </Button>
              </Tooltip>
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
