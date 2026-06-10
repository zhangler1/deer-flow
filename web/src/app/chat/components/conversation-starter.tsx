// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

import { motion } from "framer-motion";
import { ChevronRight } from "lucide-react";
import { useTranslations } from "next-intl";

import { cn } from "~/lib/utils";

import { Welcome } from "./welcome";

export function ConversationStarter({
  className,
  onSend,
}: {
  className?: string;
  onSend?: (message: string) => void;
}) {
  const t = useTranslations("chat");
  const questions = t.raw("conversationStarters") as string[];

  return (
    <div className={cn("flex flex-col items-center", className)}>
      <div className="pointer-events-none fixed inset-0 flex items-center justify-center">
        <Welcome className="pointer-events-auto mb-15 w-[75%] -translate-y-24" />
      </div>
      {/* 快捷问题列表：平铺在输入框正上方 */}
      <ul className="flex flex-col gap-3 w-full max-w-2xl">
        {questions.map((question, index) => (
          <motion.li
            key={question}
            className="flex shrink-0 active:scale-[0.98]"
            style={{ transition: "all 0.2s ease-out" }}
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{
              duration: 0.2,
              delay: index * 0.1 + 0.5,
              ease: "easeOut",
            }}
          >
            <div
              className="bg-muted/50 hover:bg-muted/80 text-foreground flex items-center justify-between h-auto w-full cursor-pointer rounded-xl px-4 py-3.5 leading-relaxed transition-all duration-200 hover:shadow-sm group"
              onClick={() => {
                onSend?.(question);
              }}
            >
              <span className="flex-1 text-sm">{question}</span>
              <ChevronRight className="h-4 w-4 text-muted-foreground group-hover:text-foreground transition-colors flex-shrink-0 ml-2" />
            </div>
          </motion.li>
        ))}
      </ul>
    </div>
  );
}
