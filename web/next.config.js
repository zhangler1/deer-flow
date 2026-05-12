/**
 * Run `build` or `dev` with `SKIP_ENV_VALIDATION` to skip env validation. This is especially useful
 * for Docker builds.
 */
// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

import "./src/env.js";
import createNextIntlPlugin from 'next-intl/plugin';

const withNextIntl = createNextIntlPlugin('./src/i18n.ts');

// DeerFlow leverages **Turbopack** during development for faster builds and a smoother developer experience.
// However, in production, **Webpack** is used instead.
//
// This decision is based on the current recommendation to avoid using Turbopack for critical projects, as it
// is still evolving and may not yet be fully stable for production environments.

// 子路径部署支持：构建时通过 NEXT_PUBLIC_BASE_PATH 注入（如 /deep-research-deerflow）。
// 未设置时按根路径部署，行为与此前一致。
const basePath = process.env.NEXT_PUBLIC_BASE_PATH ?? "";

/** @type {import("next").NextConfig} */
const config = {
  // For development mode
  turbopack: {
    rules: {
      "*.md": {
        loaders: ["raw-loader"],
        as: "*.js",
      },
    },
  },

  // For production mode
  webpack: (config) => {
    config.module.rules.push({
      test: /\.md$/,
      use: "raw-loader",
    });
    return config;
  },

  // ... rest of the configuration.
  output: "standalone",
  basePath,
  assetPrefix: basePath || undefined,

  // Docker 构建优先跟通运行时正确性，此处关闭构建阶段的 ESLint / 类型检查阻断。
  // lint 和严格类型检查由 `pnpm lint` / `pnpm typecheck` 在 CI 中独立执行，
  // 避免本地/镜像打包被非阻断性问题卡住。
  eslint: {
    ignoreDuringBuilds: true,
  },
  typescript: {
    // 着急时可打开；TS 类型错误建议还是修，默认不关闭。
    ignoreBuildErrors: false,
  },
};

export default withNextIntl(config);
