// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

import { create } from "zustand";

import type { MCPServerMetadata, SimpleMCPServerMetadata } from "../mcp";

const SETTINGS_KEY = "deerflow.settings";

const DEFAULT_SETTINGS: SettingsState = {
  general: {
    autoAcceptedPlan: false,
    enableDeepThinking: false,
    enableBackgroundInvestigation: true,  // 默认开启背景调研
    maxPlanIterations: 2,
    maxStepNum: 5,
    maxSearchResults: 2,
    searchEngine: "custom_search",
    useBudgetControlledOnlineSearch: true,  // 默认使用budget控制的在线检索
    useBudgetControlledBocomSearch: true,   // 默认使用budget控制的bocom搜索
    reportStyle: "business_marketing",  // 默认为对公营销报告
    forceRoutingPath: "deep_research", // 调试模式默认路由设置为交心深度研究
  },
  mcp: {
    servers: [],
  },
  tokens: {
    guwpToken: "",
  },
};

export type SettingsState = {
  general: {
    autoAcceptedPlan: boolean;
    enableDeepThinking: boolean;
    enableBackgroundInvestigation: boolean;
    maxPlanIterations: number;
    maxStepNum: number;
    maxSearchResults: number;
    searchEngine: "tavily" | "duckduckgo" | "brave_search" | "arxiv" | "wikipedia" | "custom_search";
    useBudgetControlledOnlineSearch: boolean;  // 是否使用budget控制的在线检索
    useBudgetControlledBocomSearch: boolean;   // 是否使用budget控制的bocom搜索
    reportStyle: "academic" | "popular_science" | "news" | "social_media" | "business_marketing" | "business_marketing_client" | "industry_report";
    forceRoutingPath?: "direct_answer" | "simple_search" | "iterative_research" | "deep_research"; // 限制调试模式路由路径选项
  };
  mcp: {
    servers: MCPServerMetadata[];
  };
  tokens: {
    guwpToken: string;
  };
};

export const useSettingsStore = create<SettingsState>(() => ({
  ...DEFAULT_SETTINGS,
}));

export const useSettings = (key: keyof SettingsState) => {
  return useSettingsStore((state) => state[key]);
};

export const changeSettings = (settings: SettingsState) => {
  useSettingsStore.setState(settings);
};

export const loadSettings = () => {
  if (typeof window === "undefined") {
    return;
  }
  const json = localStorage.getItem(SETTINGS_KEY);
  if (json) {
    const settings = JSON.parse(json);
    for (const key in DEFAULT_SETTINGS.general) {
      if (!(key in settings.general)) {
        settings.general[key as keyof SettingsState["general"]] =
          DEFAULT_SETTINGS.general[key as keyof SettingsState["general"]];
      }
    }

    try {
      useSettingsStore.setState(settings);
    } catch (error) {
      console.error(error);
    }
  }
};

export const saveSettings = () => {
  const latestSettings = useSettingsStore.getState();
  const json = JSON.stringify(latestSettings);
  localStorage.setItem(SETTINGS_KEY, json);
};

export const getChatStreamSettings = () => {
  let mcpSettings:
    | {
        servers: Record<
          string,
          MCPServerMetadata & {
            enabled_tools: string[];
            add_to_agents: string[];
          }
        >;
      }
    | undefined = undefined;
  const { mcp, general, tokens } = useSettingsStore.getState();
  const mcpServers = mcp.servers.filter((server) => server.enabled);
  if (mcpServers.length > 0) {
    mcpSettings = {
      servers: mcpServers.reduce((acc, cur) => {
        const { transport, env, headers } = cur;
        let server: SimpleMCPServerMetadata;
        if (transport === "stdio") {
          server = {
            name: cur.name,
            transport,
            env,
            command: cur.command,
            args: cur.args,
          };
        } else {
          server = {
            name: cur.name,
            transport,
            headers,
            url: cur.url,
          };
        }
        return {
          ...acc,
          [cur.name]: {
            ...server,
            enabled_tools: cur.tools.map((tool) => tool.name),
            add_to_agents: ["researcher"],
          },
        };
      }, {}),
    };
  }
  return {
    ...general,
    searchEngine: general.searchEngine, // 添加搜索引擎设置
    useBudgetControlledOnlineSearch: general.useBudgetControlledOnlineSearch, // 添加budget控制的在线检索设置
    useBudgetControlledBocomSearch: general.useBudgetControlledBocomSearch, // 添加budget控制的bocom搜索设置
    mcpSettings,
    forceRoutingPath: general.forceRoutingPath, // 添加调试模式路由路径设置
    guwpToken: tokens.guwpToken,
  };
};

export function setReportStyle(
  value: "academic" | "popular_science" | "news" | "social_media" | "business_marketing" | "business_marketing_client" | "industry_report",
) {
  useSettingsStore.setState((state) => ({
    general: {
      ...state.general,
      reportStyle: value,
    },
  }));
  saveSettings();
}

export function setEnableDeepThinking(value: boolean) {
  useSettingsStore.setState((state) => ({
    general: {
      ...state.general,
      enableDeepThinking: value,
    },
  }));
  saveSettings();
}

export function setEnableBackgroundInvestigation(value: boolean) {
  useSettingsStore.setState((state) => ({
    general: {
      ...state.general,
      enableBackgroundInvestigation: value,
    },
  }));
  saveSettings();
}
loadSettings();
