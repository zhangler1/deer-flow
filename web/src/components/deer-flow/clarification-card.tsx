"use client";

import { useState, useCallback } from "react";
import { HelpCircle, Check, Edit3 } from "lucide-react";

import { cn } from "~/lib/utils";
import { Button } from "~/components/ui/button";
import type { Option } from "~/core/messages";

interface ClarificationCardProps {
  question: string;
  options: Option[];
  onSelect: (value: string) => void;
  disabled?: boolean;
}

const OPTION_LABELS = ["A", "B", "C", "D", "E", "F"];

/**
 * 问题澄清卡片组件
 *
 * 展示 AI 生成的澄清问题及选项（3 个 AI 选项 + 1 个自定义答案），
 * 用户选择后触发 onSelect 回调。
 */
export function ClarificationCard({
  question,
  options,
  onSelect,
  disabled = false,
}: ClarificationCardProps) {
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null);
  const [customValue, setCustomValue] = useState("");

  const handleOptionClick = useCallback(
    (index: number) => {
      if (disabled) return;
      setSelectedIndex(index);
      // 如果点击的是 editable 选项，聚焦输入框由 UI 自动处理
    },
    [disabled],
  );

  const handleConfirm = useCallback(() => {
    if (selectedIndex === null || disabled) return;
    const option = options[selectedIndex];
    if (!option) return;

    if (option.editable) {
      // 自定义答案：发送输入框内容
      if (customValue.trim()) {
        onSelect(customValue.trim());
      }
    } else {
      // 固定选项：发送选项的 value
      onSelect(option.value || option.text);
    }
  }, [selectedIndex, customValue, options, onSelect, disabled]);

  const canConfirm =
    selectedIndex !== null &&
    (!options[selectedIndex]?.editable || customValue.trim().length > 0);

  return (
    <div
      className={cn(
        "mx-auto my-4 w-full max-w-lg rounded-xl border bg-card p-5 shadow-sm",
        disabled && "pointer-events-none opacity-60",
      )}
    >
      {/* 标题 */}
      <div className="mb-3 flex items-center gap-2 text-sm font-medium text-muted-foreground">
        <HelpCircle className="h-4 w-4" />
        <span>AI 想确认一下</span>
      </div>

      {/* 问题 */}
      <p className="mb-4 text-base font-medium leading-relaxed">{question}</p>

      {/* 选项列表 */}
      <div className="flex flex-col gap-2">
        {options.map((option, index) => {
          const isSelected = selectedIndex === index;
          const label = OPTION_LABELS[index] || String(index + 1);

          if (option.editable) {
            // 可编辑选项（自定义答案）
            return (
              <div
                key={index}
                className={cn(
                  "flex cursor-pointer items-center gap-3 rounded-lg border px-4 py-3 transition-colors",
                  isSelected
                    ? "border-primary bg-primary/5"
                    : "border-border hover:border-primary/50 hover:bg-muted/50",
                )}
                onClick={() => handleOptionClick(index)}
              >
                <span
                  className={cn(
                    "flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs font-medium",
                    isSelected
                      ? "bg-primary text-primary-foreground"
                      : "bg-muted text-muted-foreground",
                  )}
                >
                  {label}
                </span>
                <Edit3 className="h-4 w-4 shrink-0 text-muted-foreground" />
                <input
                  type="text"
                  placeholder="输入自定义答案..."
                  value={customValue}
                  onChange={(e) => {
                    setCustomValue(e.target.value);
                    if (selectedIndex !== index) {
                      setSelectedIndex(index);
                    }
                  }}
                  onFocus={() => setSelectedIndex(index)}
                  className="flex-1 bg-transparent text-sm outline-none placeholder:text-muted-foreground/60"
                  disabled={disabled}
                />
              </div>
            );
          }

          // 固定选项
          return (
            <div
              key={index}
              className={cn(
                "flex cursor-pointer items-center gap-3 rounded-lg border px-4 py-3 transition-colors",
                isSelected
                  ? "border-primary bg-primary/5"
                  : "border-border hover:border-primary/50 hover:bg-muted/50",
              )}
              onClick={() => handleOptionClick(index)}
            >
              <span
                className={cn(
                  "flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs font-medium",
                  isSelected
                    ? "bg-primary text-primary-foreground"
                    : "bg-muted text-muted-foreground",
                )}
              >
                {label}
              </span>
              <span className="flex-1 text-sm">{option.text}</span>
              {isSelected && (
                <Check className="h-4 w-4 shrink-0 text-primary" />
              )}
            </div>
          );
        })}
      </div>

      {/* 确认按钮 */}
      <div className="mt-4 flex justify-end">
        <Button
          size="sm"
          disabled={!canConfirm || disabled}
          onClick={handleConfirm}
          className="px-6"
        >
          确认选择
        </Button>
      </div>
    </div>
  );
}
