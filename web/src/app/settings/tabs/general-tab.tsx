// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

import { zodResolver } from "@hookform/resolvers/zod";
import { Settings } from "lucide-react";
import { useTranslations } from "next-intl";
import { useEffect, useMemo } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "~/components/ui/form";
import { Input } from "~/components/ui/input";
import { Label } from "~/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "~/components/ui/select";
import { Switch } from "~/components/ui/switch";
import type { SettingsState } from "~/core/store";
import { useConfig } from "~/core/api/hooks";
import type { CustomSearchRepositoryConfig } from "~/core/config";

import type { Tab } from "./types";

const generalFormSchema = z.object({
  autoAcceptedPlan: z.boolean(),
  maxPlanIterations: z.number().min(1, {
    message: "Max plan iterations must be at least 1.",
  }),
  maxStepNum: z.number().min(1, {
    message: "Max step number must be at least 1.",
  }),
  maxSearchResults: z.number().min(1, {
    message: "Max search results must be at least 1.",
  }),
  searchEngine: z.enum(["tavily", "duckduckgo", "brave_search", "arxiv", "wikipedia", "custom_search"]),
  customSearchRepository: z.string().optional(),
  // Others
  enableBackgroundInvestigation: z.boolean(),
  enableDeepThinking: z.boolean(),
  reportStyle: z.enum(["academic", "popular_science", "news", "social_media", "business_marketing", "jingke"]),
  // 🐛 Debug Mode
  forceRoutingPath: z.enum(["direct_answer", "simple_search", "iterative_research", "deep_research"]).optional(),
});

export const GeneralTab: Tab = ({
  settings,
  onChange,
}: {
  settings: SettingsState;
  onChange: (changes: Partial<SettingsState>) => void;
}) => {
  const t = useTranslations("settings.general");
  const { config } = useConfig();
  const generalSettings = useMemo(() => settings.general, [settings]);
  const form = useForm<z.infer<typeof generalFormSchema>>({
    resolver: zodResolver(generalFormSchema, undefined, undefined),
    defaultValues: generalSettings,
    mode: "all",
    reValidateMode: "onBlur",
  });

  const currentSettings = form.watch();
  const searchEngine = form.watch("searchEngine");
  
  // 获取可用的自定义搜索仓库选项
  const customSearchRepositories: CustomSearchRepositoryConfig[] = useMemo(
    () => config?.custom_search_repositories || [],
    [config]
  );
  useEffect(() => {
    let hasChanges = false;
    for (const key in currentSettings) {
      if (
        currentSettings[key as keyof typeof currentSettings] !==
        settings.general[key as keyof SettingsState["general"]]
      ) {
        hasChanges = true;
        break;
      }
    }
    if (hasChanges) {
      onChange({ general: currentSettings });
    }
  }, [currentSettings, onChange, settings]);

  return (
    <div className="flex flex-col gap-4">
      <header>
        <h1 className="text-lg font-medium">{t("title")}</h1>
      </header>
      <main>
        <Form {...form}>
          <form className="space-y-8">
            <FormField
              control={form.control}
              name="autoAcceptedPlan"
              render={({ field }) => (
                <FormItem>
                  <FormControl>
                    <div className="flex items-center gap-2">
                      <Switch
                        id="autoAcceptedPlan"
                        checked={field.value}
                        onCheckedChange={field.onChange}
                      />
                      <Label className="text-sm" htmlFor="autoAcceptedPlan">
                        {t("autoAcceptPlan")}
                      </Label>
                    </div>
                  </FormControl>
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="maxPlanIterations"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t("maxPlanIterations")}</FormLabel>
                  <FormControl>
                    <Input
                      className="w-60"
                      type="number"
                      defaultValue={field.value}
                      min={1}
                      onChange={(event) =>
                        field.onChange(parseInt(event.target.value || "0"))
                      }
                    />
                  </FormControl>
                  <FormDescription>
                    {t("maxPlanIterationsDescription")}
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="maxStepNum"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t("maxStepsOfPlan")}</FormLabel>
                  <FormControl>
                    <Input
                      className="w-60"
                      type="number"
                      defaultValue={field.value}
                      min={1}
                      onChange={(event) =>
                        field.onChange(parseInt(event.target.value || "0"))
                      }
                    />
                  </FormControl>
                  <FormDescription>{t("maxStepsDescription")}</FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="maxSearchResults"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t("maxSearchResults")}</FormLabel>
                  <FormControl>
                    <Input
                      className="w-60"
                      type="number"
                      defaultValue={field.value}
                      min={1}
                      onChange={(event) =>
                        field.onChange(parseInt(event.target.value || "0"))
                      }
                    />
                  </FormControl>
                  <FormDescription>
                    {t("maxSearchResultsDescription")}
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="searchEngine"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t("searchEngine")}</FormLabel>
                  <FormControl>
                    <Select
                      value={field.value}
                      onValueChange={field.onChange}
                    >
                      <SelectTrigger className="w-60">
                        <SelectValue placeholder={t("selectSearchEngine")} />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="tavily">
                          Tavily
                        </SelectItem>
                        <SelectItem value="duckduckgo">
                          DuckDuckGo
                        </SelectItem>
                        <SelectItem value="brave_search">
                          Brave Search
                        </SelectItem>
                        <SelectItem value="arxiv">
                          ArXiv (学术论文)
                        </SelectItem>
                        <SelectItem value="wikipedia">
                          Wikipedia
                        </SelectItem>
                        <SelectItem value="custom_search">
                          交心搜索引擎 (推荐)
                        </SelectItem>
                      </SelectContent>
                    </Select>
                  </FormControl>
                  <FormDescription>
                    {t("searchEngineDescription")}
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />
            {searchEngine === "custom_search" && customSearchRepositories.length > 0 && (
              <FormField
                control={form.control}
                name="customSearchRepository"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>{t("customSearchRepository")}</FormLabel>
                    <FormControl>
                      <Select
                        value={field.value}
                        onValueChange={field.onChange}
                      >
                        <SelectTrigger className="w-60">
                          <SelectValue placeholder={t("selectRepository")} />
                        </SelectTrigger>
                        <SelectContent>
                          {customSearchRepositories.map((repo) => (
                            <SelectItem key={repo.id} value={repo.id}>
                              <div className="flex flex-col items-start">
                                <span>{repo.name}</span>
                                <span className="text-xs text-muted-foreground">
                                  {repo.description}
                                </span>
                              </div>
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </FormControl>
                    <FormDescription>
                      {t("customSearchRepositoryDescription")}
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />
            )}
            {/* 🐛 Debug Mode: Force Routing Path */}
            <div className="border-t pt-4 mt-4">
              <h3 className="text-sm font-medium mb-3">🐛 {t("debugMode")}</h3>
              <FormField
                control={form.control}
                name="forceRoutingPath"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>{t("forceRoutingPath")}</FormLabel>
                    <FormControl>
                      <Select
                        value={field.value || "auto"}
                        onValueChange={(value) => {
                          field.onChange(value === "auto" ? undefined : value);
                        }}
                      >
                        <SelectTrigger className="w-60">
                          <SelectValue placeholder={t("autoRouting")} />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="auto">
                            {t("autoRouting")} (智能分类)
                          </SelectItem>
                          <SelectItem value="direct_answer">
                            📢 {t("directAnswer")} (Direct Answer)
                          </SelectItem>
                          <SelectItem value="simple_search">
                            🔍 {t("simpleSearch")} (Simple Search)
                          </SelectItem>
                          <SelectItem value="iterative_research">
                            🔄 {t("iterativeResearch")} (Iterative Research)
                          </SelectItem>
                          <SelectItem value="deep_research">
                            🔬 {t("deepResearch")} (Deep Research)
                          </SelectItem>
                        </SelectContent>
                      </Select>
                    </FormControl>
                    <FormDescription>
                      {t("forceRoutingPathDescription")}
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>
          </form>
        </Form>
      </main>
    </div>
  );
};
GeneralTab.displayName = "General";
GeneralTab.icon = Settings;
