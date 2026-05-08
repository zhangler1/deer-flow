// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

import { cn } from "~/lib/utils";

import styles from "./flowing-text.module.css";

/**
 * 流动高亮文本组件：通过 mask-image 线性渐变 + 动画 mask-position，
 * 实现文字亮度从右向左流动扫过的高亮效果。
 */
export function FlowingText({
  animated = true,
  className,
  children,
}: {
  animated?: boolean;
  className?: string;
  children?: React.ReactNode;
}) {
  return (
    <span className={cn(animated && styles.flowing, className)}>
      {children}
    </span>
  );
}
