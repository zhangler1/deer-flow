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

import { ConversationStarter } from "./conversation-starter";
import { InputBox } from "./input-box";
import { MessageListView } from "./message-list-view";
import { Welcome } from "./welcome";

export function MessagesBlock({ className }: { className?: string }) {
  const t = useTranslations("chat.messages");
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
      <MessageListView
        className="flex flex-grow"
        onFeedback={handleFeedback}
        onSendMessage={handleSend}
        onAtBottomChange={setIsAtBottom}
        scrollRef={messageListRef}
      />
      {!isReplay ? (
        <div className="relative flex min-h-42 shrink-0 pb-4 pl-4 pr-[26px]">
          {!responding && messageCount === 0 && (
            <ConversationStarter
              className="absolute top-[-430px] left-4"
              onSend={handleSend}
            />
          )}
          {/* 输入框上方的柔和渐变遮罩：仅保留 backdrop-blur，不附加颜色，避免与父容器背景不一致 */}
          <div
            aria-hidden
            className="pointer-events-none absolute inset-x-0 bottom-full z-10 h-10 backdrop-blur-[3px] [mask-image:linear-gradient(to_top,black_30%,transparent)]"
          />
          {/* 滚动到底部按钮：完整悬浮在输入框上方，无跨边缘视觉，边框和阴影更柔和 */}
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
          <InputBox
            className="flex-1 w-full"
            responding={responding}
            feedback={feedback}
            onSend={handleSend}
            onCancel={handleCancel}
            onRemoveFeedback={handleRemoveFeedback}
          />
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
                        // Walking deer animation, designed by @liangzhaojun. Thank you for creating it!
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
