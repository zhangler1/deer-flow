// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

import { motion } from "framer-motion";
import { useTranslations } from "next-intl";

import { AuroraText } from "~/components/magicui/aurora-text";
import { cn } from "~/lib/utils";

export function Welcome({ className, hideDescription }: { className?: string; hideDescription?: boolean }) {
  const t = useTranslations("hero");

  return (
    <motion.div
      className={cn("flex flex-col items-center justify-center gap-6", className)}
      style={{ transition: "all 0.2s ease-out" }}
      initial={{ opacity: 0, scale: 0.85 }}
      animate={{ opacity: 1, scale: 1 }}
    >
      <h1 className="text-center text-4xl font-bold md:text-5xl">
        <AuroraText className="mr-2">{t('title')}</AuroraText>
        <AuroraText>{t('subtitle')}</AuroraText>
      </h1>
      {!hideDescription && (
        <p className="max-w-3xl px-4 text-center text-base opacity-85 md:text-xl">
          {t('description')}
        </p>
      )}
    </motion.div>
  );
}
