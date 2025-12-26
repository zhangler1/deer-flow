// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

import { redirect } from 'next/navigation';

export default function HomePage() {
  // 默认重定向到问答页面
  redirect('/chat');
}
