// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

import { useCallback, useEffect, useRef } from "react";

import { extractSourceDetails } from "~/app/chat/components/report-references";
import { LoadingAnimation } from "~/components/deer-flow/loading-animation";
import { SourceAwareMarkdown } from "~/components/deer-flow/source-aware-markdown";
import { SourceDetailDrawer } from "~/components/deer-flow/source-detail-drawer";
import ReportEditor from "~/components/editor";
import { useReplay } from "~/core/replay";
import { useSourceStore } from "~/core/source-store";
import { useMessage, useStore } from "~/core/store";
import { stripThinkTags } from "~/core/utils/think-tag-parser";
import { cn } from "~/lib/utils";

import { CollapsibleReport } from "./collapsible-report";
import { ReportReferences } from "./report-references";

export function ResearchReportBlock({
  className,
  researchId,
  messageId,
  editing,
  allExpanded,
}: {
  className?: string;
  researchId: string;
  messageId: string;
  editing: boolean;
  allExpanded: boolean;
}) {
  const message = useMessage(messageId);
  const { isReplay } = useReplay();
  const setReferences = useSourceStore((s) => s.setReferences);
  const setResearchId = useSourceStore((s) => s.setResearchId);

  // 提取来源数据并设置到 store
  useEffect(() => {
    setResearchId(researchId);
    const sources = extractSourceDetails(researchId);
    
    console.group('[ResearchReportBlock] 来源数据提取');
    console.log('researchId:', researchId);
    console.log('提取到的 sources 数量:', sources.length);
    console.log('sources URLs:', sources.map(s => s.url));
    console.log('sources 详情:', sources.map(s => ({ url: s.url, title: s.title, type: s.sourceType })));
    console.groupEnd();
    
    setReferences(sources);
  }, [researchId, setResearchId, setReferences]);

  const references = useSourceStore((s) => s.references);

  const handleMarkdownChange = useCallback(
    (markdown: string) => {
      if (message) {
        // 创建新的 message 对象以确保触发响应式更新
        const updatedMessage = { ...message, content: markdown };
        
        // 更新 store
        const currentMessages = useStore.getState().messages;
        const newMessages = new Map(currentMessages);
        newMessages.set(message.id, updatedMessage);
        
        useStore.setState({
          messages: newMessages,
        });
      }
    },
    [message],
  );
  const contentRef = useRef<HTMLDivElement>(null);
  const isCompleted = message?.isStreaming === false && message?.content !== "";

  // reporter 内容过滤 think tag：流式和已完成均过滤
  const filteredContent = stripThinkTags(message?.content ?? "");
  // 编辑器内容：也过滤 think tag
  const editorContent = stripThinkTags(message?.content ?? "");

  // 流式场景：如果过滤后无正文内容（仅含未闭合的 think tag），不渲染任何内容
  const hasDisplayContent = message?.isStreaming ? filteredContent.length > 0 : true;

  // TODO: scroll to top when completed, but it's not working
  // useEffect(() => {
  //   if (isCompleted && contentRef.current) {
  //     setTimeout(() => {
  //       contentRef
  //         .current!.closest("[data-radix-scroll-area-viewport]")
  //         ?.scrollTo({
  //           top: 0,
  //           behavior: "smooth",
  //         });
  //     }, 500);
  //   }
  // }, [isCompleted]);

  return (
    <div ref={contentRef} className={cn("w-full pt-4 pb-8", className)}>
      {!isReplay && isCompleted && editing ? (
        <ReportEditor
          content={editorContent}
          onMarkdownChange={handleMarkdownChange}
        />
      ) : (
        <>
          {/* 流式输出时用 SourceAwareMarkdown（支持打字动画 + 源引用角标） */}
          {message?.isStreaming ? (
            hasDisplayContent ? (
              <SourceAwareMarkdown animated checkLinkCredibility references={references}>
                {filteredContent}
              </SourceAwareMarkdown>
            ) : null
          ) : (
            <CollapsibleReport
              content={filteredContent}
              checkLinkCredibility
              references={references}
              allExpanded={allExpanded}
            />
          )}
          {message?.isStreaming && <LoadingAnimation className="my-12" />}
          {/* 报告完成后展示参考资料 */}
          {isCompleted && <ReportReferences researchId={researchId} />}
          {/* 来源详情抽屉 */}
          <SourceDetailDrawer />
        </>
      )}
    </div>
  );
}
