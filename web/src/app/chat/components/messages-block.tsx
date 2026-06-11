// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

import { motion } from "framer-motion";
import { ArrowDown, FastForward, Play } from "lucide-react";
import { useTranslations } from "next-intl";
import { useCallback, useRef, useState } from "react";

import { RainbowText } from "~/components/deer-flow/rainbow-text";
import type { ScrollContainerRef } from "~/components/deer-flow/scroll-container";
import { Button } from "~/components/ui/button";
import {
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
} from "~/components/ui/card";
import { fastForwardReplay } from "~/core/api";
import { useReplayMetadata } from "~/core/api/hooks";
import type { Option, Resource } from "~/core/messages";
import { useReplay } from "~/core/replay";
import { sendMessage, useMessageIds, useStore } from "~/core/store";
import { resolveServiceURL } from "~/core/api/resolve-service-url";
import { env } from "~/env";
import { cn } from "~/lib/utils";

import { ChevronRight } from "lucide-react";

import { FeatureShowcase } from "./feature-showcase";
import { InputBox } from "./input-box";
import { MessageListView } from "./message-list-view";
import { Welcome } from "./welcome";

export function MessagesBlock({ className }: { className?: string }) {
  const t = useTranslations("chat.messages");
  const tChat = useTranslations("chat");
  const questions = tChat.raw("conversationStarters") as string[];
  const messageIds = useMessageIds();
  const messageCount = messageIds.length;
  const responding = useStore((state) => state.responding);
  const { isReplay } = useReplay();
  const { title: replayTitle, hasError: replayHasError } = useReplayMetadata();
  const [replayStarted, setReplayStarted] = useState(false);
  const abortControllerRef = useRef<AbortController | null>(null);
  const [feedback, setFeedback] = useState<{ option: Option } | null>(null);
  const handleSend = useCallback(
    async (
      message: string,
      options?: {
        interruptFeedback?: string;
        resources?: Array<Resource>;
        documentContexts?: Array<{ filename: string; content: string }>;
      },
    ) => {
      const abortController = new AbortController();
      abortControllerRef.current = abortController;
      try {
        await sendMessage(
          message,
          {
            interruptFeedback:
              options?.interruptFeedback ?? feedback?.option.value,
            resources: options?.resources,
            documentContexts: options?.documentContexts,
          },
          {
            abortSignal: abortController.signal,
          },
        );
      } catch {}
    },
    [feedback],
  );
  const handleCancel = useCallback(() => {
    // 双保险：前端 abort + 后端显式 cancel 接口
    // 原因：浏览器 fetch abort 后，keep-alive TCP 连接不一定立即关闭，
    // ASGI 可能收不到 http.disconnect，必须显式通知后端
    const threadId = useStore.getState().threadId;
    if (threadId) {
      fetch(resolveServiceURL("chat/cancel"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ thread_id: threadId }),
        keepalive: true,
      }).catch((err) => {
        console.warn("[handleCancel] cancel 接口调用失败", err);
      });
    }
    abortControllerRef.current?.abort();
    abortControllerRef.current = null;
  }, []);
  const handleFeedback = useCallback(
    (feedback: { option: Option }) => {
      setFeedback(feedback);
    },
    [setFeedback],
  );
  const handleRemoveFeedback = useCallback(() => {
    setFeedback(null);
  }, [setFeedback]);
  const handleStartReplay = useCallback(() => {
    setReplayStarted(true);
    void sendMessage();
  }, [setReplayStarted]);
  const [fastForwarding, setFastForwarding] = useState(false);
  const handleFastForwardReplay = useCallback(() => {
    setFastForwarding(!fastForwarding);
    fastForwardReplay(!fastForwarding);
  }, [fastForwarding]);

  // 当用户上滑离开底部时，展示“滑动到底部”按钮
  const messageListRef = useRef<ScrollContainerRef>(null);
  const [isAtBottom, setIsAtBottom] = useState(true);
  const handleScrollToBottom = useCallback(() => {
    messageListRef.current?.forceScrollToBottom();
  }, []);
  return (
    <div className={cn("flex h-full flex-col", className)}>
      {/* 可滚动区域：消息列表 或 欢迎内容（Welcome + FeatureShowcase） */}
      <MessageListView
        className="flex flex-grow"
        onFeedback={handleFeedback}
        onSendMessage={handleSend}
        onAtBottomChange={setIsAtBottom}
        scrollRef={messageListRef}
        hideScrollbar={!responding && messageCount === 0 && !isReplay}
        welcomeSlot={
          !responding && messageCount === 0 && !isReplay ? (
            <>
              <Welcome className="mb-4" hideDescription />
              <FeatureShowcase className="w-full max-w-[1000px] flex-1" />
            </>
          ) : undefined
        }
      />
      {!isReplay ? (
        <div className="relative flex flex-col shrink-0 pb-4 pl-4 pr-[26px]">
          {/* 输入框上方的柔和渐变遮罩 */}
          <div
            aria-hidden
            className="pointer-events-none absolute inset-x-0 bottom-full z-10 h-10 backdrop-blur-[3px] [mask-image:linear-gradient(to_top,black_30%,transparent)]"
          />
          {/* 滚动到底部按钮 */}
          {!isAtBottom && (
            <motion.button
              type="button"
              aria-label="滑动到底部"
              onClick={handleScrollToBottom}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 6 }}
              transition={{ duration: 0.2 }}
              className="absolute left-1/2 bottom-full mb-2 z-20 flex h-9 w-9 -translate-x-1/2 items-center justify-center rounded-full border border-border/60 bg-white/90 text-muted-foreground shadow-sm backdrop-blur-sm transition-all hover:text-foreground hover:shadow-md"
            >
              <ArrowDown size={16} />
            </motion.button>
          )}
          {/* 内容居中限宽 */}
          <div className="flex flex-col items-center w-full max-w-4xl mx-auto">
            {/* 快捷问题：紧贴输入框正上方 */}
            {!responding && messageCount === 0 && (
              <ul className="grid grid-cols-2 gap-2 w-full max-w-2xl mb-3">
                {questions.map((question, index) => (
                  <motion.li
                    key={question}
                    className="flex shrink-0 active:scale-[0.98]"
                    style={{ transition: "all 0.2s ease-out" }}
                    initial={{ opacity: 0, y: 16 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.2, delay: index * 0.08 + 0.3, ease: "easeOut" }}
                  >
                    <div
                      className="bg-muted/50 hover:bg-muted/80 text-foreground flex items-center justify-between h-auto w-full cursor-pointer rounded-lg px-3 py-2 leading-normal transition-all duration-200 hover:shadow-sm group"
                      onClick={() => handleSend(question)}
                    >
                      <span className="flex-1 text-sm">{question}</span>
                      <ChevronRight className="h-4 w-4 text-muted-foreground group-hover:text-foreground transition-colors flex-shrink-0 ml-2" />
                    </div>
                  </motion.li>
                ))}
              </ul>
            )}
            <InputBox
              className="w-full"
              responding={responding}
              feedback={feedback}
              onSend={handleSend}
              onCancel={handleCancel}
              onRemoveFeedback={handleRemoveFeedback}
            />
          </div>
        </div>
      ) : (
        <>
          <div
            className={cn(
              "fixed bottom-[calc(50vh+80px)] left-0 transition-all duration-500 ease-out",
              replayStarted && "pointer-events-none scale-150 opacity-0",
            )}
          >
            <Welcome />
          </div>
          <motion.div
            className="mb-4 h-fit w-full items-center justify-center"
            initial={{ opacity: 0, y: "20vh" }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
          >
            <Card
              className={cn(
                "w-full transition-all duration-300",
                !replayStarted && "translate-y-[-40vh]",
              )}
            >
              <div className="flex items-center justify-between">
                <div className="flex flex-grow items-center">
                  {responding && (
                    <motion.div
                      className="ml-3"
                      initial={{ opacity: 0, scale: 0.8 }}
                      animate={{ opacity: 1, scale: 1 }}
                      exit={{ opacity: 0, scale: 0.8 }}
                      transition={{ duration: 0.3 }}
                    >
                      <video
                        src="/images/walking_deer.webm"
                        autoPlay
                        loop
                        muted
                        className="h-[42px] w-[42px] object-contain"
                      />
                    </motion.div>
                  )}
                  <CardHeader className={cn("flex-grow", responding && "pl-3")}>
                    <CardTitle>
                      <RainbowText animated={responding}>
                        {responding ? t("replaying") : `${replayTitle}`}
                      </RainbowText>
                    </CardTitle>
                    <CardDescription>
                      <RainbowText animated={responding}>
                        {responding
                          ? t("replayDescription")
                          : replayStarted
                            ? t("replayHasStopped")
                            : t("replayModeDescription")}
                      </RainbowText>
                    </CardDescription>
                  </CardHeader>
                </div>
                {!replayHasError && (
                  <div className="pr-4">
                    {responding && (
                      <Button
                        className={cn(fastForwarding && "animate-pulse")}
                        variant={fastForwarding ? "default" : "outline"}
                        onClick={handleFastForwardReplay}
                      >
                        <FastForward size={16} />
                        {t("fastForward")}
                      </Button>
                    )}
                    {!replayStarted && (
                      <Button className="w-24" onClick={handleStartReplay}>
                        <Play size={16} />
                        {t("play")}
                      </Button>
                    )}
                  </div>
                )}
              </div>
            </Card>
            {!replayStarted && env.NEXT_PUBLIC_STATIC_WEBSITE_ONLY && (
              <div className="text-muted-foreground w-full text-center text-xs">
                {t("demoNotice")}{" "}
                <a
                  className="underline"
                  href="https://github.com/bytedance/deer-flow"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  {t("clickHere")}
                </a>{" "}
                {t("cloneLocally")}
              </div>
            )}
          </motion.div>
        </>
      )}
    </div>
  );
}
