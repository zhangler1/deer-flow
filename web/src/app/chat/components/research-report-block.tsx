// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

import { useCallback, useRef } from "react";

import { LoadingAnimation } from "~/components/deer-flow/loading-animation";
import { Markdown } from "~/components/deer-flow/markdown";
import ReportEditor from "~/components/editor";
import { useReplay } from "~/core/replay";
import { useMessage, useStore } from "~/core/store";
import { cn } from "~/lib/utils";

import { CollapsibleReport } from "./collapsible-report";
import { ReportReferences } from "./report-references";

export function ResearchReportBlock({
  className,
  researchId,
  messageId,
  editing,
}: {
  className?: string;
  researchId: string;
  messageId: string;
  editing: boolean;
}) {
  const message = useMessage(messageId);
  const { isReplay } = useReplay();
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
          content={message?.content}
          onMarkdownChange={handleMarkdownChange}
        />
      ) : (
        <>
          {/* 流式输出时用原始 Markdown（支持打字动画） */}
          {message?.isStreaming ? (
            <Markdown animated checkLinkCredibility>
              {message?.content}
            </Markdown>
          ) : (
            <CollapsibleReport
              content={message?.content ?? ""}
              checkLinkCredibility
            />
          )}
          {message?.isStreaming && <LoadingAnimation className="my-12" />}
          {/* 报告完成后展示参考资料 */}
          {isCompleted && <ReportReferences researchId={researchId} />}
        </>
      )}
    </div>
  );
}
