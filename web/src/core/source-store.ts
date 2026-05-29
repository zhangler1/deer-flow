import { create } from "zustand";

// ── 类型 ──────────────────────────────────────────

/** 来源详细信息 */
export interface SourceDetail {
  url: string;
  title: string;
  domain: string;
  snippet?: string;
  fullContent?: string;
  aiSummary?: string;
  sourceType: "search" | "crawl" | "knowledge";
  toolName?: string;
}

interface SourceState {
  /** 当前研究 ID */
  researchId: string | null;
  /** 所有来源引用列表 */
  references: SourceDetail[];
  /** 当前选中的来源序号 */
  selectedIndex: number | null;
  /** 当前选中的来源 URL（以 URL 为主键） */
  selectedUrl: string | null;
  /** 抽屉是否打开 */
  drawerOpen: boolean;

  /** 设置当前研究 ID */
  setResearchId: (id: string) => void;
  /** 设置来源引用列表 */
  setReferences: (refs: SourceDetail[]) => void;
  /** 按 URL 打开来源详情（主方式） */
  openSourceByUrl: (url: string) => void;
  /** 按序号打开来源详情（备选） */
  openSourceByIndex: (index: number) => void;
  /** 关闭抽屉 */
  closeDrawer: () => void;
}

export const useSourceStore = create<SourceState>((set, get) => ({
  researchId: null,
  references: [],
  selectedIndex: null,
  selectedUrl: null,
  drawerOpen: false,

  setResearchId: (id) => set({ researchId: id }),

  setReferences: (refs) => set({ references: refs }),

  openSourceByUrl: (url) => {
    const { references } = get();
    const index = references.findIndex((r) => r.url === url);
    set({
      selectedUrl: url,
      selectedIndex: index >= 0 ? index : null,
      drawerOpen: true,
    });
  },

  openSourceByIndex: (index) => {
    const { references } = get();
    const ref = references[index];
    set({
      selectedIndex: index,
      selectedUrl: ref?.url ?? null,
      drawerOpen: true,
    });
  },

  closeDrawer: () =>
    set({
      drawerOpen: false,
      selectedIndex: null,
      selectedUrl: null,
    }),
}));
