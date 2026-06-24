"use client";

import { Home, Search, FileText, Clock, ChevronRight, Building2 } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";

import { Button } from "~/components/ui/button";
import { Input } from "~/components/ui/input";
import {
  fetchCurrentUser,
  fetchMyReports,
  fetchReportContent,
  type ReportRecord,
  type UserInfo,
} from "~/core/api/dashboard";
import { useStore } from "~/core/store";
import { useGuipInfo } from "~/hooks/use-guip-info";
import { cn } from "~/lib/utils";

export function HistoryDrawer() {
  const drawerOpen = useStore((s) => s.drawerOpen);
  const openReportViewer = useStore((s) => s.openReportViewer);

  const [reports, setReports] = useState<ReportRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [keyword, setKeyword] = useState("");
  const [loadingContentId, setLoadingContentId] = useState<string | null>(null);
  const [user, setUser] = useState<UserInfo | null>(null);

  // GUIP 用户信息（从 GuipAPI.xc2.js 获取）
  const { userInfo: guipUser } = useGuipInfo();

  const PAGE_SIZE = 20;
  const hasMore = reports.length < total;
  const debounceTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const loadReports = useCallback(
    async (resetPage: boolean) => {
      setLoading(true);
      try {
        const nextPage = resetPage ? 1 : page;
        const resp = await fetchMyReports({
          page: nextPage,
          page_size: PAGE_SIZE,
          keyword: keyword || undefined,
          status: "completed",
        });
        if (resetPage) {
          setReports(resp.items);
        } else {
          setReports((prev) => [...prev, ...resp.items]);
        }
        setTotal(resp.total);
        setPage(nextPage + 1);
      } catch (err) {
        console.error("[HistoryDrawer] 加载报告列表失败:", err);
      } finally {
        setLoading(false);
      }
    },
    [page, keyword],
  );

  // 加载当前用户信息
  useEffect(() => {
    fetchCurrentUser()
      .then(setUser)
      .catch((err) => console.error("[HistoryDrawer] 加载用户信息失败:", err));
  }, []);

  // 首次加载 + 搜索词变化时重置并加载
  useEffect(() => {
    if (!drawerOpen) return;
    if (debounceTimer.current) clearTimeout(debounceTimer.current);
    debounceTimer.current = setTimeout(() => {
      setPage(1);
      loadReports(true);
    }, 300);
    return () => {
      if (debounceTimer.current) clearTimeout(debounceTimer.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [drawerOpen, keyword]);

  // 打开抽屉时首次加载
  useEffect(() => {
    if (drawerOpen && reports.length === 0 && !loading) {
      loadReports(true);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [drawerOpen]);

  const handleClickReport = useCallback(
    async (report: ReportRecord) => {
      setLoadingContentId(report.id);
      try {
        const data = await fetchReportContent(report.id);
        openReportViewer(report.id, data.content, data.title);
      } catch (err) {
        console.error("[HistoryDrawer] 读取报告内容失败:", err);
      } finally {
        setLoadingContentId(null);
      }
    },
    [openReportViewer],
  );

  const handleGoHome = useCallback(() => {
    useStore.getState().closeReportViewer();
    useStore.setState({ drawerOpen: false });
  }, []);

  const formatDuration = (ms: number | null) => {
    if (!ms) return "";
    if (ms < 1000) return `${ms}ms`;
    const seconds = Math.floor(ms / 1000);
    if (seconds < 60) return `${seconds}s`;
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}m${secs}s`;
  };

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return "";
    const d = new Date(dateStr);
    const month = (d.getMonth() + 1).toString().padStart(2, "0");
    const day = d.getDate().toString().padStart(2, "0");
    const hour = d.getHours().toString().padStart(2, "0");
    const min = d.getMinutes().toString().padStart(2, "0");
    return `${month}-${day} ${hour}:${min}`;
  };

  /** 取用户名首字符作为头像：汉字取第一个汉字，英文取首字母大写 */
  const getAvatarChar = (name: string) => {
    if (!name) return "?";
    const ch = name.charAt(0);
    return /[\u4e00-\u9fa5]/.test(ch) ? ch : ch.toUpperCase();
  };

  return (
    <>
      {/* 遮罩层 */}
      {drawerOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/20 transition-opacity"
          onClick={() => useStore.getState().toggleDrawer()}
        />
      )}

      {/* 抽屉主体 */}
      <div
        className={cn(
          "fixed left-0 top-12 bottom-0 z-50 flex w-[280px] flex-col border-r border-gray-200 bg-white shadow-lg transition-transform duration-300 ease-in-out",
          drawerOpen ? "translate-x-0" : "-translate-x-full",
        )}
      >
        {/* 顶部：首页按钮 */}
        <div className="flex items-center gap-2 border-b border-gray-100 px-4 py-3">
          <Button
            variant="ghost"
            size="sm"
            className="flex w-full items-center justify-start gap-2 text-gray-700 hover:bg-gray-100"
            onClick={handleGoHome}
          >
            <Home className="h-4 w-4" />
            <span className="text-sm font-medium">首页</span>
          </Button>
        </div>

        {/* 搜索框 */}
        <div className="px-4 py-3">
          <div className="relative">
            <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-gray-400" />
            <Input
              placeholder="搜索报告标题..."
              value={keyword}
              onChange={(e) => setKeyword(e.target.value)}
              className="h-8 pl-8 text-sm"
            />
          </div>
        </div>

        {/* 列表标题 */}
        <div className="px-4 pb-2">
          <span className="text-xs font-medium text-gray-500 uppercase tracking-wider">
            历史对话
          </span>
          {total > 0 && (
            <span className="ml-1 text-xs text-gray-400">({total})</span>
          )}
        </div>

        {/* 报告列表 */}
        <div className="flex-1 min-h-0 overflow-y-auto px-2">
          {loading && reports.length === 0 ? (
            <div className="flex items-center justify-center py-8">
              <div className="h-5 w-5 animate-spin rounded-full border-2 border-blue-500 border-t-transparent" />
            </div>
          ) : reports.length === 0 ? (
            <div className="px-2 py-8 text-center text-sm text-gray-400">
              {keyword ? "未找到匹配的报告" : "暂无历史报告"}
            </div>
          ) : (
            <div className="flex flex-col gap-0.5">
              {reports.map((report) => (
                <button
                  key={report.id}
                  className={cn(
                    "flex w-full flex-col gap-1 rounded-lg px-3 py-2.5 text-left transition-colors hover:bg-gray-50",
                    loadingContentId === report.id && "opacity-60",
                  )}
                  onClick={() => handleClickReport(report)}
                  disabled={loadingContentId === report.id}
                >
                  <div className="flex items-start gap-2">
                    <FileText className="mt-0.5 h-3.5 w-3.5 shrink-0 text-blue-500" />
                    <span className="line-clamp-2 text-sm font-medium text-gray-800 leading-tight">
                      {report.title}
                    </span>
                  </div>
                  <div className="flex items-center gap-2 pl-5.5 text-xs text-gray-400">
                    <span>{formatDate(report.created_at)}</span>
                    {report.duration_ms && (
                      <>
                        <span>·</span>
                        <Clock className="h-3 w-3" />
                        <span>{formatDuration(report.duration_ms)}</span>
                      </>
                    )}
                  </div>
                </button>
              ))}
            </div>
          )}

          {/* 加载更多 */}
          {hasMore && !loading && (
            <div className="py-2">
              <Button
                variant="ghost"
                size="sm"
                className="w-full text-xs text-gray-500"
                onClick={() => loadReports(false)}
              >
                加载更多
                <ChevronRight className="ml-1 h-3 w-3" />
              </Button>
            </div>
          )}
          {loading && reports.length > 0 && (
            <div className="flex items-center justify-center py-3">
              <div className="h-4 w-4 animate-spin rounded-full border-2 border-blue-500 border-t-transparent" />
            </div>
          )}
        </div>
        {/* 底部：用户信息（优先 GUIP，降级 dashboard） */}
        {(() => {
          // 优先展示 GUIP 用户信息
          const name = guipUser?.userName || guipUser?.loginName;
          const org = guipUser?.linkedOrgName;
          if (name) {
            return (
              <div className="flex items-center gap-3 border-t border-gray-100 px-4 py-3">
                <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-blue-500 text-sm font-medium text-white select-none">
                  {getAvatarChar(name)}
                </div>
                <div className="flex min-w-0 flex-col">
                  <span className="truncate text-sm font-medium text-gray-700">{name}</span>
                  {org && (
                    <span className="flex items-center gap-1 truncate text-xs text-gray-400">
                      <Building2 className="h-3 w-3 shrink-0" />
                      {org}
                    </span>
                  )}
                </div>
              </div>
            );
          }
          // 降级：dashboard 用户信息
          if (user?.is_authenticated) {
            return (
              <div className="flex items-center gap-3 border-t border-gray-100 px-4 py-3">
                <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-blue-500 text-sm font-medium text-white select-none">
                  {getAvatarChar(user.user_name || user.login_name)}
                </div>
                <span className="truncate text-sm text-gray-700">{user.login_name}</span>
              </div>
            );
          }
          return null;
        })()}
      </div>
    </>
  );
}
