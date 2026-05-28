// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

import { useTranslations } from "next-intl";
import { Cpu } from "lucide-react";

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "~/components/ui/dropdown-menu";
import { setReporterModel, useSettingsStore } from "~/core/store";
import { useConfig } from "~/core/api/hooks";
import { cn } from "~/lib/utils";

import { Tooltip } from "./tooltip";

// 右箭头图标 - 与 ReportStyleDialog 一致
function ChevronDownIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="currentColor"
      xmlns="http://www.w3.org/2000/svg"
    >
      <path
        d="M8.88318 1.29785C9.27087 1.08594 9.75721 1.22853 9.96912 1.61621L14.9105 10.6572C15.3679 11.4941 15.3679 12.5059 14.9105 13.3428L9.96912 22.3838C9.75721 22.7715 9.27087 22.9141 8.88318 22.7021C8.4955 22.4902 8.35292 22.0039 8.56482 21.6162L13.5072 12.5752C13.7029 12.2168 13.7029 11.7832 13.5072 11.4248L8.56482 2.38379C8.35292 1.9961 8.4955 1.50977 8.88318 1.29785Z"
        fill="currentColor"
      />
    </svg>
  );
}

// 选中勾选图标 - 与 ReportStyleDialog 一致
function CheckMarkIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="currentColor"
      xmlns="http://www.w3.org/2000/svg"
    >
      <path
        d="M21.0082 6.43261C21.3244 6.12129 21.8347 6.12303 22.1487 6.43652C22.4627 6.75002 22.4609 7.25605 22.1448 7.56738L11.3999 18.1475C10.8493 18.6896 9.96106 18.6896 9.41049 18.1475L2.85524 11.6924C2.53909 11.381 2.53734 10.875 2.85131 10.5615C3.14573 10.2675 3.61293 10.2475 3.93072 10.5029L3.99178 10.5576L10.4052 16.8721L21.0082 6.43261Z"
        fill="currentColor"
      />
    </svg>
  );
}

export function ReporterModelSelector() {
  const t = useTranslations("settings.reporterModel");
  const { config } = useConfig();
  const currentModel = useSettingsStore((state) => state.general.reporterModel);

  // 从 /api/config 获取 reporter_options
  const reporterOptions = config?.reporter_options;
  const options = reporterOptions?.options ?? [];
  const defaultKey = reporterOptions?.default ?? "";

  // 当前选中的 key：优先用户选择，其次 default
  const selectedKey = currentModel || defaultKey;

  // 找到当前选中项的显示名
  const selectedOption = options.find((opt) => opt.key === selectedKey);
  const displayModel = selectedOption?.model ?? selectedKey;

  // 没有可选模型时不渲染
  if (options.length === 0) {
    return null;
  }

  return (
    <DropdownMenu>
      <Tooltip
        className="max-w-60"
        title={
          <div>
            <h3 className="mb-2 font-bold">
              {t("model")}: {displayModel}
            </h3>
            <p>{t("chooseDesc")}</p>
          </div>
        }
      >
        <DropdownMenuTrigger asChild>
          <button
            className={cn(
              "relative cursor-pointer flex box-border rounded-xl px-5 py-3",
              "!text-[14px] !leading-[22px] h-8 pr-3",
              "transition-colors duration-150 ease-out",
              "bg-transparent text-brand hover:bg-accent outline-none",
              "items-center gap-1 shrink-0 select-none whitespace-nowrap",
            )}
          >
            <Cpu className="shrink-0 size-[18px]" />
            <span className="min-w-0 truncate flex items-center gap-0.5">
              {displayModel}
              <ChevronDownIcon className="size-3 opacity-50" />
            </span>
          </button>
        </DropdownMenuTrigger>
      </Tooltip>
      <DropdownMenuContent
        align="start"
        className="w-[280px] p-[3.5px] rounded-lg overflow-hidden"
      >
        {options.map((option) => {
          const isSelected = selectedKey === option.key;

          return (
            <DropdownMenuItem
              key={option.key}
              className={cn(
                "flex items-center gap-2 px-2.5 py-2 rounded-md cursor-pointer",
                isSelected && "bg-accent",
              )}
              onClick={() => setReporterModel(option.key)}
            >
              {/* 左侧图标 */}
              <div className="mr-1 flex size-4 shrink-0 mt-[3px] text-foreground">
                <Cpu className="size-4" />
              </div>
              {/* 中间：模型名 */}
              <div className="flex-1 flex flex-col leading-[22px]">
                <div className="truncate mb-0.5 h-5 leading-5 text-left text-sm">
                  {option.model}
                </div>
                <div
                  className="truncate font-normal text-xs leading-[18px] text-muted-foreground text-left"
                >
                  {option.key}
                </div>
              </div>
              {/* 右侧勾选 */}
              <div className="flex h-5 items-center self-start ml-2">
                {isSelected && <CheckMarkIcon className="size-4 text-primary" />}
              </div>
            </DropdownMenuItem>
          );
        })}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
