"use client";

import { useState, useCallback, useMemo } from "react";
import {
  HelpCircle,
  Check,
  Edit3,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";

import { cn } from "~/lib/utils";
import { Button } from "~/components/ui/button";
import type { ClarificationQuestion } from "~/core/messages";

interface ClarificationCardProps {
  /** 多个澄清问题（问卷模式） */
  questions: ClarificationQuestion[];
  /** 全部问题回答完后回调，传入每题的答案数组 */
  onSubmit: (answers: string[]) => void;
  /** 是否已提交（提交后卡片保留，显示已回答状态） */
  submitted?: boolean;
  disabled?: boolean;
}

const OPTION_LABELS = ["A", "B", "C", "D", "E", "F"];

/**
 * 问题澄清问卷卡片组件
 *
 * 支持多个问题逐题展示、上/下题导航、进度指示、全部回答后确认提交。
 * 提交后卡片不消失，进入已回答只读状态。
 */
export function ClarificationCard({
  questions,
  onSubmit,
  submitted = false,
  disabled = false,
}: ClarificationCardProps) {
  const [currentIndex, setCurrentIndex] = useState(0);
  // answers[i]: 第 i 题的答案（空字符串表示未回答）
  const [answers, setAnswers] = useState<string[]>(
    () => new Array(questions.length).fill(""),
  );
  // 每题当前选中的选项索引
  const [selectedIndices, setSelectedIndices] = useState<(number | null)[]>(
    () => new Array(questions.length).fill(null),
  );
  // 每题自定义输入值
  const [customValues, setCustomValues] = useState<string[]>(
    () => new Array(questions.length).fill(""),
  );

  const total = questions.length;
  const current = questions[currentIndex];
  const isLocked = submitted || disabled;

  // 判断所有题是否都已回答
  const allAnswered = useMemo(
    () => answers.every((a) => a.length > 0),
    [answers],
  );

  // 选择某题的选项
  const handleOptionClick = useCallback(
    (optionIndex: number) => {
      if (isLocked) return;
      const newIndices = [...selectedIndices];
      newIndices[currentIndex] = optionIndex;
      setSelectedIndices(newIndices);

      const option = current?.options[optionIndex];
      if (option && !option.editable) {
        // 固定选项：直接记录答案
        const newAnswers = [...answers];
        newAnswers[currentIndex] = option.value || option.text;
        setAnswers(newAnswers);
      } else {
        // 可编辑选项：答案由 customValue 驱动
        const newAnswers = [...answers];
        newAnswers[currentIndex] = customValues[currentIndex] || "";
        setAnswers(newAnswers);
      }
    },
    [isLocked, selectedIndices, currentIndex, current, answers, customValues],
  );

  // 自定义输入变化
  const handleCustomChange = useCallback(
    (value: string) => {
      if (isLocked) return;
      const newCustom = [...customValues];
      newCustom[currentIndex] = value;
      setCustomValues(newCustom);

      // 同步答案
      const editableIdx = current?.options.findIndex((o) => o.editable) ?? -1;
      if (selectedIndices[currentIndex] === editableIdx) {
        const newAnswers = [...answers];
        newAnswers[currentIndex] = value.trim();
        setAnswers(newAnswers);
      }
    },
    [isLocked, customValues, currentIndex, current, selectedIndices, answers],
  );

  // 导航
  const goPrev = useCallback(() => {
    if (currentIndex > 0) setCurrentIndex(currentIndex - 1);
  }, [currentIndex]);

  const goNext = useCallback(() => {
    if (currentIndex < total - 1) setCurrentIndex(currentIndex + 1);
  }, [currentIndex, total]);

  // 全部提交
  const handleSubmit = useCallback(() => {
    if (!allAnswered || isLocked) return;
    onSubmit(answers);
  }, [allAnswered, isLocked, onSubmit, answers]);

  if (!current) return null;

  return (
    <div
      className={cn(
        "mx-auto my-4 w-full max-w-lg rounded-xl border bg-card p-5 shadow-sm",
        isLocked && "pointer-events-none opacity-70",
      )}
    >
      {/* 标题栏 */}
      <div className="mb-3 flex items-center justify-between">
        <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
          <HelpCircle className="h-4 w-4" />
          <span>{submitted ? "AI 确认完毕" : "AI 想确认一下"}</span>
        </div>
        {/* 进度指示 */}
        <span className="text-xs text-muted-foreground">
          {currentIndex + 1} / {total}
        </span>
      </div>

      {/* 当前问题 */}
      <p className="mb-4 text-base font-medium leading-relaxed">
        {current.question}
      </p>

      {/* 选项列表 */}
      <div className="flex flex-col gap-2">
        {current.options.map((option, index) => {
          const isSelected = selectedIndices[currentIndex] === index;
          const label = OPTION_LABELS[index] || String(index + 1);

          if (option.editable) {
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
                  value={customValues[currentIndex]}
                  onChange={(e) => handleCustomChange(e.target.value)}
                  onFocus={() => handleOptionClick(index)}
                  className="flex-1 bg-transparent text-sm outline-none placeholder:text-muted-foreground/60"
                  disabled={isLocked}
                />
              </div>
            );
          }

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

      {/* 底部操作栏：导航 + 确认 */}
      <div className="mt-4 flex items-center justify-between">
        {/* 上一题/下一题 */}
        <div className="flex items-center gap-1">
          <Button
            variant="ghost"
            size="sm"
            disabled={currentIndex === 0 || isLocked}
            onClick={goPrev}
            className="gap-1 px-2"
          >
            <ChevronLeft className="h-4 w-4" />
            上一题
          </Button>
          <Button
            variant="ghost"
            size="sm"
            disabled={currentIndex === total - 1 || isLocked}
            onClick={goNext}
            className="gap-1 px-2"
          >
            下一题
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>

        {/* 确认按钮 */}
        <Button
          size="sm"
          disabled={!allAnswered || isLocked}
          onClick={handleSubmit}
          className="px-6"
        >
          {submitted ? "已提交" : "确认提交"}
        </Button>
      </div>
    </div>
  );
}
