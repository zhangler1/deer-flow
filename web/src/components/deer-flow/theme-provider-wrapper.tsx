// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

"use client";

import { usePathname } from "next/navigation";
import { useEffect } from "react";
import { useTheme } from "next-themes";

import { ThemeProvider } from "~/components/theme-provider";

function ThemeClassApplier({ children }: { children: React.ReactNode }) {
  const { theme } = useTheme();

  useEffect(() => {
    const root = document.documentElement;
    
    // 移除所有主题类
    root.classList.remove('theme-jiaoxin', 'theme-sunset');
    
    // 根据主题添加对应的类名
    if (theme === 'jiaoxin') {
      root.classList.add('theme-jiaoxin');
    } else if (theme === 'sunset') {
      root.classList.add('theme-sunset');
    }
  }, [theme]);

  return <>{children}</>;
}

export function ThemeProviderWrapper({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const isChatPage = pathname?.startsWith("/chat");

  return (
    <ThemeProvider
      attribute="class"
      defaultTheme={"light"}
      enableSystem={isChatPage}
      forcedTheme={isChatPage ? undefined : "light"}
      disableTransitionOnChange
    >
      <ThemeClassApplier>{children}</ThemeClassApplier>
    </ThemeProvider>
  );
}
