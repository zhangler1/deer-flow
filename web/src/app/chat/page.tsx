// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

"use client";

import { ChevronLeft } from "lucide-react";
import dynamic from "next/dynamic";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { Suspense } from "react";

import { Tooltip } from "~/components/deer-flow/tooltip";
import { Button } from "~/components/ui/button";

import { Logo } from "../../components/deer-flow/logo";
import { ThemeToggle } from "../../components/deer-flow/theme-toggle";
import { SettingsDialog } from "../settings/dialogs/settings-dialog";

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
        <div className="flex items-center gap-2">
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
        <div className="flex items-center">
          <ThemeToggle />
          {/* <Suspense>
            <SettingsDialog />
          </Suspense> */}
        </div>
      </header>
      <Main />
    </div>
  );
}
