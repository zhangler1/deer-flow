// SPDX-License-Identifier: MIT

import { resolveServiceURL } from "./resolve-service-url";

/**
 * 从后端获取历史报告的平均生成耗时（毫秒）。
 *
 * 如果数据库无数据或接口异常，则回退到 default_duration_ms。
 * 返回值为 0 表示无可用历史数据，调用方可自行决定兜底值。
 */
export async function fetchAvgDuration(): Promise<number> {
  const res = await fetch(resolveServiceURL("research/avg-duration"), {
    credentials: "include",
  });
  if (!res.ok) return 0;
  const data = (await res.json()) as {
    avg_duration_ms: number;
    default_duration_ms: number;
  };
  // 有历史数据则返回历史均值，否则返回后端提供的默认值
  return data.avg_duration_ms > 0
    ? data.avg_duration_ms
    : data.default_duration_ms;
}
