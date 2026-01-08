// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

"use client";

import { useTranslations } from "next-intl";
import { Layers, RotateCw } from "lucide-react";

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "~/components/ui/select";
import { useSettingsStore, saveSettings } from "~/core/store";
import { cn } from "~/lib/utils";

import { Tooltip } from "./tooltip";

const RESEARCH_TYPES = [
  {
    value: "deep_research" as const,
    labelKey: "deepResearch",
    icon: Layers,
  },
  {
    value: "iterative_research" as const,
    labelKey: "iterativeResearch",
    icon: RotateCw,
  },
];

export function ResearchTypeSelector() {
  const t = useTranslations("settings.researchType");
  const forceRoutingPath = useSettingsStore(
    (state) => state.general.forceRoutingPath,
  );

  const handleTypeChange = (
    value: "deep_research" | "iterative_research",
  ) => {
    useSettingsStore.setState((state) => ({
      general: {
        ...state.general,
        forceRoutingPath: value,
      },
    }));
    saveSettings();
  };

  const currentType =
    RESEARCH_TYPES.find((type) => type.value === forceRoutingPath) ||
    RESEARCH_TYPES[0]!;
  const CurrentIcon = currentType.icon;

  return (
    <Tooltip
      className="max-w-60"
      title={
        <div>
          <h3 className="mb-2 font-bold">
            {t("researchType")}: {t(currentType.labelKey)}
          </h3>
          <p>{t("chooseDesc")}</p>
        </div>
      }
    >
      <Select value={forceRoutingPath} onValueChange={handleTypeChange}>
        <SelectTrigger
          className={cn(
            "h-8 w-auto gap-2 rounded-2xl border px-3 text-sm",
            "!border-brand !text-brand",
          )}
        >
          <div className="flex items-center gap-2">
            <CurrentIcon className="h-4 w-4 shrink-0 text-white" />
            <span className="whitespace-nowrap">{t(currentType.labelKey)}</span>
          </div>
        </SelectTrigger>
        <SelectContent>
          {RESEARCH_TYPES.map((type) => {
            const Icon = type.icon;
            return (
              <SelectItem key={type.value} value={type.value}>
                <div className="flex items-center gap-2">
                  <Icon className="h-4 w-4 text-white" />
                  <span>{t(type.labelKey)}</span>
                </div>
              </SelectItem>
            );
          })}
        </SelectContent>
      </Select>
    </Tooltip>
  );
}
