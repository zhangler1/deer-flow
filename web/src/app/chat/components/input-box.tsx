// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

import { MagicWandIcon } from "@radix-ui/react-icons";
import { AnimatePresence, motion } from "framer-motion";
import { ArrowUp, Paperclip, X } from "lucide-react";
import { useTranslations } from "next-intl";
import { useCallback, useEffect, useRef, useState } from "react";

import AttachmentUpload, {
  type AttachmentFile,
  type AttachmentUploadRef,
} from "~/components/deer-flow/attachment-upload";
import { Detective } from "~/components/deer-flow/icons/detective";
import MessageInput, {
  type MessageInputRef,
} from "~/components/deer-flow/message-input";
import { ReportStyleDialog } from "~/components/deer-flow/report-style-dialog";
import { ReporterModelSelector } from "~/components/deer-flow/reporter-model-selector";
import { ResearchTypeSelector } from "~/components/deer-flow/research-type-selector";
import { Tooltip } from "~/components/deer-flow/tooltip";
import { UploadMask } from "~/components/deer-flow/upload-mask";
import { BorderBeam } from "~/components/magicui/border-beam";
import { Button } from "~/components/ui/button";
import { enhancePrompt } from "~/core/api";
import { useConfig } from "~/core/api/hooks";
import type { Option, Resource } from "~/core/messages";
import {
  setEnableBackgroundInvestigation,
  setReporterModel,
  useSettingsStore,
} from "~/core/store";
import { cn } from "~/lib/utils";

export function InputBox({
  className,
  responding,
  feedback,
  onSend,
  onCancel,
  onRemoveFeedback,
}: {
  className?: string;
  size?: "large" | "normal";
  responding?: boolean;
  feedback?: { option: Option } | null;
  onSend?: (
    message: string,
    options?: {
      interruptFeedback?: string;
      resources?: Array<Resource>;
      documentContexts?: Array<{ filename: string; content: string }>;
    },
  ) => void;
  onCancel?: () => void;
  onRemoveFeedback?: () => void;
}) {
  const t = useTranslations("chat.inputBox");
  const tCommon = useTranslations("common");
  const tSettings = useTranslations("settings.general");
  const backgroundInvestigation = useSettingsStore(
    (state) => state.general.enableBackgroundInvestigation,
  );

  const { config, loading } = useConfig();
  const reportStyle = useSettingsStore((state) => state.general.reportStyle);
  const reporterModel = useSettingsStore((state) => state.general.reporterModel);
  const containerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<MessageInputRef>(null);
  const feedbackRef = useRef<HTMLDivElement>(null);
  const attachmentRef = useRef<AttachmentUploadRef>(null);

  const MAX_CHARS = 3000;

  const [isEnhancing, setIsEnhancing] = useState(false);
  const [isEnhanceAnimating, setIsEnhanceAnimating] = useState(false);
  const [currentPrompt, setCurrentPrompt] = useState("");
  const [isDragOver, setIsDragOver] = useState(false);
  const [attachments, setAttachments] = useState<AttachmentFile[]>([]);

  // 当配置加载后，如果 reporterModel 为空，则用 default 初始化
  useEffect(() => {
    if (config?.reporter_options?.default && !reporterModel) {
      setReporterModel(config.reporter_options.default);
    }
  }, [config, reporterModel]);

  const handleSendMessage = useCallback(
    (message: string, resources: Array<Resource>) => {
      if (responding) {
        onCancel?.();
      } else {
        if (message.trim() === "") {
          return;
        }
        if (onSend) {
          const documentContexts =
            attachmentRef.current?.getSuccessfulAttachments() || [];
          onSend(message, {
            interruptFeedback: feedback?.option.value,
            resources,
            documentContexts:
              documentContexts.length > 0 ? documentContexts : undefined,
          });
          onRemoveFeedback?.();
          // Clear enhancement animation after sending
          setIsEnhanceAnimating(false);
          // Immediately reset counter, avoid waiting for debounced onUpdate
          setCurrentPrompt("");
        }
      }
    },
    [responding, onCancel, onSend, feedback, onRemoveFeedback],
  );

  // Drag and drop handlers
  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.dataTransfer.types.includes("Files")) {
      setIsDragOver(true);
    }
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      setIsDragOver(false);
      const files = e.dataTransfer?.files;
      if (files && files.length > 0) {
        attachmentRef.current?.addFiles(Array.from(files));
      }
    },
    [],
  );

  const handleEnhancePrompt = useCallback(async () => {
    if (currentPrompt.trim() === "" || isEnhancing) {
      return;
    }

    setIsEnhancing(true);
    setIsEnhanceAnimating(true);

    try {
      const enhancedPrompt = await enhancePrompt({
        prompt: currentPrompt,
        report_style: reportStyle.toUpperCase(),
      });

      // Add a small delay for better UX
      await new Promise((resolve) => setTimeout(resolve, 500));

      // Update the input with the enhanced prompt with animation
      if (inputRef.current) {
        inputRef.current.setContent(enhancedPrompt);
        setCurrentPrompt(enhancedPrompt);
      }

      // Keep animation for a bit longer to show the effect
      setTimeout(() => {
        setIsEnhanceAnimating(false);
      }, 1000);
    } catch (error) {
      console.error("Failed to enhance prompt:", error);
      setIsEnhanceAnimating(false);
      // Could add toast notification here
    } finally {
      setIsEnhancing(false);
    }
  }, [currentPrompt, isEnhancing, reportStyle]);

  return (
    <div
      className={cn(
        "bg-card relative flex w-full flex-col rounded-[24px] border",
        className,
      )}
      ref={containerRef}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      <UploadMask visible={isDragOver} />
      {/* Attachment area - inside input box, top-left aligned */}
      <AttachmentUpload
        ref={attachmentRef}
        maxFiles={5}
        maxSizeMB={2}
        disabled={responding}
        onChange={setAttachments}
      />
      <div className="w-full">
        <AnimatePresence>
          {feedback && (
            <motion.div
              ref={feedbackRef}
              className="bg-background border-brand absolute top-0 left-0 mt-2 ml-4 flex items-center justify-center gap-1 rounded-2xl border px-2 py-0.5"
              initial={{ opacity: 0, scale: 0 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0 }}
              transition={{ duration: 0.2, ease: "easeInOut" }}
            >
              <div className="text-brand flex h-full w-full items-center justify-center text-sm opacity-90">
                {feedback.option.text}
              </div>
              <X
                className="cursor-pointer opacity-60"
                size={16}
                onClick={onRemoveFeedback}
              />
            </motion.div>
          )}
          {isEnhanceAnimating && (
            <motion.div
              className="pointer-events-none absolute inset-0 z-20"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.3 }}
            >
              <div className="relative h-full w-full">
                {/* Sparkle effect overlay */}
                <motion.div
                  className="absolute inset-0 rounded-[24px] bg-gradient-to-r from-blue-500/10 via-purple-500/10 to-blue-500/10"
                  animate={{
                    background: [
                      "linear-gradient(45deg, rgba(59, 130, 246, 0.1), rgba(147, 51, 234, 0.1), rgba(59, 130, 246, 0.1))",
                      "linear-gradient(225deg, rgba(147, 51, 234, 0.1), rgba(59, 130, 246, 0.1), rgba(147, 51, 234, 0.1))",
                      "linear-gradient(45deg, rgba(59, 130, 246, 0.1), rgba(147, 51, 234, 0.1), rgba(59, 130, 246, 0.1))",
                    ],
                  }}
                  transition={{ duration: 2, repeat: Infinity }}
                />
                {/* Floating sparkles */}
                {[...Array(6)].map((_, i) => (
                  <motion.div
                    key={i}
                    className="absolute h-2 w-2 rounded-full bg-blue-400"
                    style={{
                      left: `${20 + i * 12}%`,
                      top: `${30 + (i % 2) * 40}%`,
                    }}
                    animate={{
                      y: [-10, -20, -10],
                      opacity: [0, 1, 0],
                      scale: [0.5, 1, 0.5],
                    }}
                    transition={{
                      duration: 1.5,
                      repeat: Infinity,
                      delay: i * 0.2,
                    }}
                  />
                ))}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
        <MessageInput
          className={cn(
            "h-24 px-4 pt-5",
            feedback && "pt-9",
            isEnhanceAnimating && "transition-all duration-500",
          )}
          ref={inputRef}
          loading={loading}
          config={config}
          onEnter={handleSendMessage}
          onChange={setCurrentPrompt}
          maxLength={MAX_CHARS}
        />
      </div>
      <div className="flex items-center px-4 py-2">
        <div className="flex grow gap-2">
          {/* 暂时隐藏研究类型选择器 */}
          {/* <ResearchTypeSelector /> */}
          {/* 暂时隐藏背景调研按钮 */}
          {/* <Tooltip
            className="max-w-60"
            title={
              <div>
                <h3 className="mb-2 font-bold">
                  {t("investigationTooltip.title", {
                    status: backgroundInvestigation ? t("on") : t("off"),
                  })}
                </h3>
                <p>{t("investigationTooltip.description")}</p>
              </div>
            }
          >
            <Button
              className={cn(
                "rounded-2xl",
                backgroundInvestigation && "!border-brand !text-brand",
              )}
              variant="outline"
              onClick={() =>
                setEnableBackgroundInvestigation(!backgroundInvestigation)
              }
            >
              <Detective /> {t("investigation")}
            </Button>
          </Tooltip> */}
          <Tooltip title="上传文档">
            <Button
              variant="outline"
              size="icon"
              className="h-9 w-9 rounded-2xl"
              onClick={() => attachmentRef.current?.triggerSelect()}
              disabled={responding}
            >
              <Paperclip className="h-4 w-4" />
            </Button>
          </Tooltip>
          <ReportStyleDialog />
          <ReporterModelSelector />
        </div>
        <div className="flex shrink-0 items-center justify-center gap-1 px-2">
          <span
            className={cn(
              "text-xs tabular-nums",
              currentPrompt.length >= MAX_CHARS
                ? "text-red-500"
                : "text-muted-foreground",
            )}
          >
            {currentPrompt.length.toLocaleString()}/{MAX_CHARS.toLocaleString()}
          </span>
          {currentPrompt.length >= MAX_CHARS && (
            <span className="text-xs text-red-500 whitespace-nowrap">
              已超出字数限制
            </span>
          )}
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <Tooltip
            className="max-w-60"
            title={
              isEnhancing || currentPrompt.trim() === ""
                ? t("enhancePromptDisabledTooltip")
                : t("enhancePromptTooltip")
            }
          >
            <span className="inline-flex">
              <Button
                variant="ghost"
                size="icon"
                className={cn(
                  "hover:bg-accent h-10 w-10",
                  isEnhancing && "animate-pulse",
                )}
                onClick={handleEnhancePrompt}
                disabled={isEnhancing || currentPrompt.trim() === ""}
              >
                {isEnhancing ? (
                  <div className="flex h-10 w-10 items-center justify-center">
                    <div className="bg-foreground h-3 w-3 animate-bounce rounded-full opacity-70" />
                  </div>
                ) : (
                  <MagicWandIcon className="text-brand" />
                )}
              </Button>
            </span>
          </Tooltip>
          <Tooltip
            className="max-w-60"
            title={responding ? t("stopTooltip") : t("sendTooltip")}
          >
            <Button
              variant="outline"
              size="icon"
              className={cn("h-10 w-10 rounded-full")}
              onClick={() => inputRef.current?.submit()}
            >
              {responding ? (
                <div className="flex h-10 w-10 items-center justify-center">
                  <div className="bg-foreground h-4 w-4 rounded-sm opacity-70" />
                </div>
              ) : (
                <ArrowUp />
              )}
            </Button>
          </Tooltip>
        </div>
      </div>
      {isEnhancing && (
        <>
          <BorderBeam
            duration={5}
            size={250}
            className="from-transparent via-red-500 to-transparent"
          />
          <BorderBeam
            duration={5}
            delay={3}
            size={250}
            className="from-transparent via-blue-500 to-transparent"
          />
        </>
      )}
    </div>
  );
}
