// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

"use client";

import { FileUp } from "lucide-react";

import { cn } from "~/lib/utils";

interface UploadMaskProps {
  visible: boolean;
  className?: string;
}

export function UploadMask({ visible, className }: UploadMaskProps) {
  if (!visible) return null;

  return (
    <div
      className={cn(
        "pointer-events-none absolute inset-0 z-50 flex items-center justify-center",
        "rounded-xl border-2 border-dashed border-[#99c8ff] dark:border-[#3060a0]",
        "bg-[#f0f4fd] dark:bg-[#0e1825] backdrop-blur-[1px]",
        "animate-in fade-in duration-200",
        className,
      )}
    >
      <div className="flex flex-col items-center gap-2 text-primary">
        <FileUp className="h-8 w-8 animate-bounce" />
        <span className="text-sm font-medium">松开以上传文件</span>
      </div>
    </div>
  );
}
