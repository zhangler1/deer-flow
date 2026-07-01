// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

"use client";

import { BarChart3, ChevronLeft, PanelLeftClose, PanelLeftOpen } from "lucide-react";
import dynamic from "next/dynamic";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { Suspense, useEffect, useState } from "react";

import { Tooltip } from "~/components/deer-flow/tooltip";
import { Button } from "~/components/ui/button";
import { fetchCurrentUser, type UserInfo } from "~/core/api/dashboard";
import { useStore } from "~/core/store";

import { Logo } from "../../components/deer-flow/logo";

import { HistoryDrawer } from "./components/history-drawer";
import { ReportViewer } from "./components/report-viewer";

const Main = dynamic(() => import("./main"), {
  ssr: false,
  loading: () => (
    <div className="flex h-full w-full items-center justify-center">
      Loading 交心深度研究...
    </div>
  ),
});

export default function HomePage() {
  const t = useTranslations("chat.page");
  const router = useRouter();
  const drawerOpen = useStore((s) => s.drawerOpen);
  const toggleDrawer = useStore((s) => s.toggleDrawer);
  const viewingReportId = useStore((s) => s.viewingReportId);
  const [isAdmin, setIsAdmin] = useState(false);

  useEffect(() => {
    fetchCurrentUser()
      .then((u) => setIsAdmin(u.is_admin === true))
      .catch(() => setIsAdmin(false));
  }, []);

  const handleBack = () => {
    if (window.history.length > 1) {
      router.back();
    } else {
      router.push('/');
    }
  };

  return (
    <div className="flex h-screen w-screen justify-center overscroll-none bg-white">
      <header
        className="fixed top-0 left-0 flex h-12 w-full items-center justify-between px-4 z-50 border-b border-gray-200/60"
        style={{
          background: "linear-gradient(to right, rgba(249,250,251,0.92) calc(16px + var(--header-split, 0px)), rgba(255,255,255,0.92) calc(16px + var(--header-split, 0px)))",
          backdropFilter: "blur(8px)",
          WebkitBackdropFilter: "blur(8px)",
        }}
      >
        <div className="flex items-center gap-1">
          <Tooltip title={drawerOpen ? "收起侧栏" : "展开历史报告"}>
            <Button
              variant="ghost"
              size="icon"
              onClick={toggleDrawer}
              className="h-9 w-9"
            >
              {drawerOpen ? (
                <PanelLeftClose className="h-5 w-5" />
              ) : (
                <PanelLeftOpen className="h-5 w-5" />
              )}
            </Button>
          </Tooltip>
          <Tooltip title="返回上一页">
            <Button
              variant="ghost"
              size="icon"
              onClick={handleBack}
              className="h-9 w-9"
            >
              <ChevronLeft className="h-5 w-5" />
            </Button>
          </Tooltip>
          <Logo />
        </div>
        <div className="flex items-center gap-1">
          {isAdmin && (
            <Tooltip title="数据看板">
              <Button
                variant="ghost"
                size="icon"
                onClick={() => router.push("/dashboard")}
                className="h-9 w-9"
              >
                <BarChart3 className="h-5 w-5" />
              </Button>
            </Tooltip>
          )}
          {/* <Suspense>
            <SettingsDialog />
          </Suspense> */}
        </div>
      </header>

      {/* 左侧历史报告抽屉 */}
      <HistoryDrawer />

      {/* 主内容区：报告回看 or 对话 */}
      {viewingReportId ? (
        <div className="h-full w-full pt-12">
          <ReportViewer />
        </div>
      ) : (
        <Main />
      )}
    </div>
  );
}
