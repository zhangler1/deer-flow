// SPDX-License-Identifier: MIT

"use client";

import { useRouter } from "next/navigation";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <header className="border-b border-gray-200 bg-white px-6 py-4 dark:border-gray-700 dark:bg-gray-800">
        <div className="flex items-center justify-between">
          <h1 className="text-xl font-semibold text-gray-900 dark:text-white">
            数据看板
          </h1>
          <button
            onClick={() => router.push("/chat")}
            className="text-sm text-blue-600 hover:text-blue-800 dark:text-blue-400 cursor-pointer"
          >
            返回主页
          </button>
        </div>
      </header>
      <main className="p-6">{children}</main>
    </div>
  );
}
