"use client";

import { ArrowLeft, Check, ChevronsDownUp, ChevronsUpDown, Copy, Download, Loader2, MessageSquare, Pencil, Save, Undo2, X } from "lucide-react";
import { useCallback, useState } from "react";
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
import { resolveServiceURL } from "~/core/api/resolve-service-url";
import { continueReport, fetchReportContent, saveReportContent } from "~/core/api/dashboard";
import { useStore } from "~/core/store";
import { stripThinkTags } from "~/core/utils/think-tag-parser";
import { cn } from "~/lib/utils";

import ReportEditor from "~/components/editor";

import { CollapsibleReport } from "./collapsible-report";

export function ReportViewer({ className }: { className?: string }) {
  const reportId = useStore((s) => s.viewingReportId);
  const content = useStore((s) => s.viewingReportContent);
  const title = useStore((s) => s.viewingReportTitle);
  const closeReportViewer = useStore((s) => s.closeReportViewer);

  const [copied, setCopied] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [continuing, setContinuing] = useState(false);
  const [sectionsExpanded, setSectionsExpanded] = useState(false);
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [dirty, setDirty] = useState(false);

  const filteredContent = content ? stripThinkTags(content) : "";

  const handleCopy = useCallback(() => {
    if (!filteredContent) return;
    if (navigator.clipboard?.writeText) {
      void navigator.clipboard.writeText(filteredContent);
    } else {
      const textArea = document.createElement("textarea");
      textArea.value = filteredContent;
      textArea.style.position = "fixed";
      textArea.style.left = "-999999px";
      document.body.appendChild(textArea);
      textArea.focus();
      textArea.select();
      try {
        document.execCommand("copy");
      } catch (err) {
        console.error("[ReportViewer] copy failed:", err);
      } finally {
        document.body.removeChild(textArea);
      }
    }
    setCopied(true);
    setTimeout(() => setCopied(false), 1000);
  }, [filteredContent]);

  const handleDownload = useCallback(
    async () => {
      if (!filteredContent) return;
      const now = new Date();
      const pad = (n: number) => n.toString().padStart(2, "0");
      const timestamp = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}_${pad(now.getHours())}-${pad(now.getMinutes())}-${pad(now.getSeconds())}`;
      const filename = `research-report-${timestamp}`;

      try {
        setDownloading(true);
        const res = await fetch(resolveServiceURL("markdown/to_word/encrypted"), {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ content: filteredContent, filename }),
        });
        if (res.ok) {
          const blob = await res.blob();
          const url = URL.createObjectURL(blob);
          const a = document.createElement("a");
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
        console.warn(`[ReportViewer] Word 转换失败 (status=${res.status})`);
        toast.error("文档下载失败，请稍后重试");
      } catch (err) {
        console.warn("[ReportViewer] Word conversion failed:", err);
        toast.error("网络异常，下载失败");
      } finally {
        setDownloading(false);
      }
    },
    [filteredContent],
  );

  const handleEdit = useCallback(() => {
    setEditing((v) => !v);
  }, []);

  const handleMarkdownChange = useCallback(
    (markdown: string) => {
      // 更新本地查看内容（不影响 MinIO 存储）
      useStore.setState({ viewingReportContent: markdown });
      setDirty(true);
    },
    [],
  );

  const handleSave = useCallback(async () => {
    if (!reportId) return;
    const currentContent = useStore.getState().viewingReportContent ?? filteredContent;
    setSaving(true);
    try {
      await saveReportContent(reportId, currentContent);
      setDirty(false);
      toast.success("报告已保存");
    } catch (err) {
      console.error("[ReportViewer] save failed:", err);
      toast.error("保存失败，请稍后重试");
    } finally {
      setSaving(false);
    }
  }, [reportId, filteredContent]);

  const handleContinueConversation = useCallback(async () => {
    if (!reportId) return;
    setContinuing(true);
    try {
      const data = await continueReport(reportId);
      // 设置继续对话上下文（供消息列表显示卡片 + 发送时注入 documentContexts）
      useStore.getState().setContinuingReportContext({
        reportId,
        title: data.title,
        content: data.report_content,
      });
      // 关闭报告查看器，回到对话界面
      closeReportViewer();
    } catch (err) {
      console.error("[ReportViewer] continue conversation failed:", err);
    } finally {
      setContinuing(false);
    }
  }, [reportId, closeReportViewer]);

  if (!reportId || !content) return null;

  return (
    <div className={cn("flex h-full w-full flex-col", className)}>
      <Card className="flex h-full w-full flex-col">
        {/* 顶部操作栏 —— 固定高度，不与滚动区重叠 */}
        <div className="flex shrink-0 items-center justify-between px-4 py-2 border-b border-gray-100">
          <div className="flex items-center gap-2 min-w-0">
            <Tooltip title="返回列表">
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8 shrink-0 text-gray-500"
                onClick={closeReportViewer}
              >
                <ArrowLeft className="h-4 w-4" />
              </Button>
            </Tooltip>
            <span className="text-sm font-medium text-gray-700 truncate">
              {title}
            </span>
          </div>

          <div className="flex shrink-0 items-center gap-1">
            <Tooltip title={sectionsExpanded ? "折叠全部" : "展开全部"}>
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8 text-gray-400"
                onClick={() => setSectionsExpanded((v) => !v)}
              >
                {sectionsExpanded ? (
                  <ChevronsDownUp className="h-4 w-4" />
                ) : (
                  <ChevronsUpDown className="h-4 w-4" />
                )}
              </Button>
            </Tooltip>

            <Tooltip title={editing ? "退出编辑" : "编辑"}>
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8 text-gray-400"
                onClick={handleEdit}
              >
                {editing ? (
                  <Undo2 className="h-4 w-4" />
                ) : (
                  <Pencil className="h-4 w-4" />
                )}
              </Button>
            </Tooltip>

            {(editing || dirty) && (
              <Tooltip title={dirty ? "保存修改" : "保存"}>
                <Button
                  variant="ghost"
                  size="icon"
                  className={cn(
                    "h-8 w-8",
                    dirty ? "text-blue-500" : "text-gray-400",
                  )}
                  disabled={saving || !dirty}
                  onClick={handleSave}
                >
                  {saving ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Save className="h-4 w-4" />
                  )}
                </Button>
              </Tooltip>
            )}

            <Tooltip title="复制">
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8 text-gray-400"
                onClick={handleCopy}
              >
                {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
              </Button>
            </Tooltip>

            <DropdownMenu>
              <Tooltip title="下载报告">
                <DropdownMenuTrigger asChild>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-8 w-8 text-gray-400"
                    disabled={downloading}
                  >
                    {downloading ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <Download className="h-4 w-4" />
                    )}
                  </Button>
                </DropdownMenuTrigger>
              </Tooltip>
              <DropdownMenuContent align="end" className="min-w-[140px]">
                <DropdownMenuItem
                  className="flex cursor-pointer items-center gap-2"
                  onClick={() => handleDownload()}
                >
                  <span>Word</span>
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>

            <Tooltip title="关闭">
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8 text-gray-400"
                onClick={closeReportViewer}
              >
                <X className="h-4 w-4" />
              </Button>
            </Tooltip>
          </div>
        </div>

        {/* 报告正文 */}
        <ScrollContainer className="min-h-0 flex-1 px-8 pb-20" scrollShadowColor="var(--card)">
          <div className="mx-auto max-w-3xl py-8">
            {editing ? (
              <ReportEditor
                content={filteredContent}
                onMarkdownChange={handleMarkdownChange}
              />
            ) : (
              <CollapsibleReport
                content={filteredContent}
                checkLinkCredibility={false}
                references={[]}
                allExpanded={sectionsExpanded}
              />
            )}

            {/* 继续对话按钮 */}
            <div className="mt-12 flex justify-center border-t border-gray-100 pt-8">
              <Button
                variant="default"
                size="lg"
                className="gap-2"
                disabled={continuing}
                onClick={handleContinueConversation}
              >
                {continuing ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <MessageSquare className="h-4 w-4" />
                )}
                基于此报告继续对话
              </Button>
            </div>
          </div>
        </ScrollContainer>
      </Card>
    </div>
  );
}
