// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

"use client";

import dynamic from "next/dynamic";
import { useTranslations } from "next-intl";
import { Suspense } from "react";
import { ChevronLeft } from "lucide-react";
import { useRouter } from "next/navigation";

import { Logo } from "../../components/deer-flow/logo";
import { ThemeToggle } from "../../components/deer-flow/theme-toggle";
import { SettingsDialog } from "../settings/dialogs/settings-dialog";
import { Button } from "~/components/ui/button";
import { Tooltip } from "~/components/deer-flow/tooltip";

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
    <div className="flex h-screen w-screen justify-center overscroll-none">
      <header className="fixed top-0 left-0 flex h-12 w-full items-center justify-between px-4">
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
          <Suspense>
            <SettingsDialog />
          </Suspense>
        </div>
      </header>
      <Main />
    </div>
  );
}
