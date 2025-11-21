// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

"use client";

import { motion, AnimatePresence } from "framer-motion";
import { Search } from "lucide-react";
import { useTranslations } from "next-intl";

import { LoadingAnimation } from "~/components/deer-flow/loading-animation";
import { useStore } from "~/core/store";
import { cn } from "~/lib/utils";

export function SearchStatusBar({ className }: { className?: string }) {
  const t = useTranslations("chat.search");
  const searchStatus = useStore((state) => state.searchStatus);

  return (
    <AnimatePresence>
      {searchStatus && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -10 }}
          transition={{ duration: 0.2 }}
          className={cn(
            "flex items-center gap-3 px-4 py-2.5 rounded-full border border-primary/20 bg-primary/5 shadow-sm",
            className
          )}
        >
          <Search size={16} className="text-primary shrink-0" />
          <div className="flex-1 min-w-0">
            <span className="text-sm font-medium text-foreground truncate block">
              {t("searching")}: {searchStatus.query}
            </span>
            {searchStatus.repository && (
              <span className="text-xs text-muted-foreground truncate block">
                {t("repository")}: {searchStatus.repository}
              </span>
            )}
          </div>
          <LoadingAnimation className="scale-50 shrink-0" />
        </motion.div>
      )}
    </AnimatePresence>
  );
}
