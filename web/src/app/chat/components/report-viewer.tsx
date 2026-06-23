"use client";

import { ArrowLeft, Check, ChevronsDownUp, ChevronsUpDown, Copy, Download, Loader2, MessageSquare, Pencil, Undo2, X } from "lucide-react";
import { useCallback, useState } from "react";

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
import { continueReport, fetchReportContent } from "~/core/api/dashboard";
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
    async (format: "docx" | "markdown") => {
      if (!filteredContent) return;
      const now = new Date();
      const pad = (n: number) => n.toString().padStart(2, "0");
      const timestamp = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}_${pad(now.getHours())}-${pad(now.getMinutes())}-${pad(now.getSeconds())}`;
      const filename = `research-report-${timestamp}`;

      if (format === "markdown") {
        const blob = new Blob([filteredContent], { type: "text/markdown" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
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

      try {
        setDownloading(true);
        const res = await fetch(resolveServiceURL("markdown/to_word"), {
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
      } catch (err) {
        console.warn("[ReportViewer] Word conversion failed:", err);
      } finally {
        setDownloading(false);
      }

      // Fallback: download markdown
      const blob = new Blob([filteredContent], { type: "text/markdown" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${filename}.md`;
      document.body.appendChild(a);
      a.click();
      setTimeout(() => {
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
      }, 0);
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
    },
    [],
  );

  const handleContinueConversation = useCallback(async () => {
    if (!reportId) return;
    setContinuing(true);
    try {
      const data = await continueReport(reportId);
      // 将报告内容存入 store，供 messages-block 发送第一条消息时注入
      useStore.setState({
        viewingReportContent: data.report_content,
        viewingReportTitle: data.title,
        viewingReportId: reportId,
      });
      // 关闭报告查看器，回到对话界面
      // 注意：不清空 viewingReportContent，让 messages-block 检测到后注入上下文
      closeReportViewer();
    } catch (err) {
      console.error("[ReportViewer] continue conversation failed:", err);
    } finally {
      setContinuing(false);
    }
  }, [reportId, closeReportViewer]);

  if (!reportId || !content) return null;

  return (
    <div className={cn("h-full w-full", className)}>
      <Card className="relative h-full w-full pt-4">
        {/* 顶部操作栏 */}
        <div className="absolute left-4 top-3 flex items-center gap-2">
          <Tooltip title="返回列表">
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8 text-gray-500"
              onClick={closeReportViewer}
            >
              <ArrowLeft className="h-4 w-4" />
            </Button>
          </Tooltip>
          <span className="text-sm font-medium text-gray-700 line-clamp-1 max-w-[300px]">
            {title}
          </span>
        </div>

        <div className="absolute right-4 top-3 flex items-center gap-1">
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
                onClick={() => handleDownload("docx")}
              >
                <span>Word</span>
              </DropdownMenuItem>
              <DropdownMenuItem
                className="flex cursor-pointer items-center gap-2"
                onClick={() => handleDownload("markdown")}
              >
                <span>Markdown</span>
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

        {/* 报告正文 */}
        <ScrollContainer className="h-full px-8 pb-20" scrollShadowColor="var(--card)">
          <div className="mx-auto max-w-3xl pt-8">
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
