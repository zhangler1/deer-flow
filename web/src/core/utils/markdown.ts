/**
 * 客户端引用归一化工具。
 *
 * 后端 reporter 节点会通过 `normalize_citations` 把 [N] / 【N】 / [[N]] / （N）
 * 等变体引用统一转换为 [(N)](URL)，再交给前端 ReactMarkdown 解析为 <a> 标签，
 * 最终由 SourceAwareMarkdown 渲染为 SourceTag 小圆圈。
 *
 * 但实际场景中：
 *   - 后端改造尚未部署 / 服务未重启
 *   - 流式输出时 `reference_index` 事件滞后到达，导致后端无法回填 URL
 *   - 模型直接吐出 （N） / [N] / 【N】 等不被 Markdown 解析为链接的纯文本
 *
 * 为此在前端做一次兜底归一化：利用 useSourceStore.references（含 index 字段），
 * 把上述变体都替换为 [(N)](URL)，让前端同样能渲染为小圆圈。
 *
 * 注意：
 *   - 只替换 N 在 [1, references.length] 范围内的引用，避免误伤正文中的
 *     "（1）月份"等自然语言编号。
 *   - 不修改已经是 [(N)](URL) 的链接（前一个字符是 `(` 跳过）。
 *   - markdown 转义序列 \[N]（参考资料区列表）保持原样。
 */

export interface CitationRef {
  /** 引用编号（从 1 开始） */
  index: number;
  /** 引用 URL */
  url: string;
}

/**
 * 归一化所有变体引用标记为 [(N)](URL)。
 *
 * 支持的输入变体：
 *   - `[N]`         英文方括号
 *   - `【N】`       中文方括号
 *   - `[[N]]`       双方括号
 *   - `（N）`       中文全角圆括号
 *
 * @param markdown 原始 markdown 文本
 * @param refs 引用映射，index 从 1 开始
 * @returns 归一化后的 markdown
 */
export function normalizeCitations(
  markdown: string,
  refs: CitationRef[],
): string {
  if (!markdown || refs.length === 0) return markdown;

  // 构建反向索引：index -> url
  const indexToUrl = new Map<number, string>();
  for (const r of refs) {
    if (r.url && r.index >= 1) {
      indexToUrl.set(r.index, r.url);
    }
  }
  if (indexToUrl.size === 0) return markdown;

  const maxIndex = Math.max(...indexToUrl.keys());

  /**
   * 在原文本上做一次闭包替换，避免链式匹配与回溯。
   * JS String.replace 自带一次性扫描，左到右扫描原字符串，
   * 在闭包内构造的目标字符串不会再被当前正则二次匹配。
   */
  const safeReplace = (
    text: string,
    pattern: RegExp,
    build: (n: number) => string,
  ): string => {
    return text.replace(pattern, (match, numStr, offset) => {
      const n = parseInt(numStr, 10);
      if (n < 1 || n > maxIndex) return match;
      const url = indexToUrl.get(n);
      if (!url) return match;
      // 前一个字符是 `(` → 已经是 [(N)](URL) 的一部分，不动
      if (offset > 0) {
        const prev = text[offset - 1];
        if (prev === "(" || prev === "\\") return match;
      }
      return build(n);
    });
  };

  let result = markdown;

  // 模式 1：[N] 英文方括号
  result = safeReplace(result, /\[(\d+)\]/g, (n) => `[(${n})](${indexToUrl.get(n)})`);

  // 模式 2：【N】中文方括号
  result = result.replace(/【(\d+)】/g, (match, numStr) => {
    const n = parseInt(numStr, 10);
    if (n < 1 || n > maxIndex) return match;
    const url = indexToUrl.get(n);
    if (!url) return match;
    return `[(${n})](${url})`;
  });

  // 模式 3：[[N]] 双方括号
  result = result.replace(/\[\[(\d+)\]\]/g, (match, numStr) => {
    const n = parseInt(numStr, 10);
    if (n < 1 || n > maxIndex) return match;
    const url = indexToUrl.get(n);
    if (!url) return match;
    return `[(${n})](${url})`;
  });

  // 模式 4：（N）中文全角圆括号
  result = result.replace(/（(\d+)）/g, (match, numStr) => {
    const n = parseInt(numStr, 10);
    if (n < 1 || n > maxIndex) return match;
    const url = indexToUrl.get(n);
    if (!url) return match;
    return `[(${n})](${url})`;
  });

  return result;
}

export function autoFixMarkdown(markdown: string): string {
  return autoCloseTrailingLink(markdown);
}

function autoCloseTrailingLink(markdown: string): string {
  // Fix unclosed Markdown links or images
  let fixedMarkdown: string = markdown;

  // Fix unclosed image syntax ![...](...)
  fixedMarkdown = fixedMarkdown.replace(
    /!\[([^\]]*)\]\(([^)]*)$/g,
    (match: string, altText: string, url: string): string => {
      return `![${altText}](${url})`;
    },
  );

  // Fix unclosed link syntax [...](...)
  fixedMarkdown = fixedMarkdown.replace(
    /\[([^\]]*)\]\(([^)]*)$/g,
    (match: string, linkText: string, url: string): string => {
      return `[${linkText}](${url})`;
    },
  );

  // Fix unclosed image syntax ![...]
  fixedMarkdown = fixedMarkdown.replace(
    /!\[([^\]]*)$/g,
    (match: string, altText: string): string => {
      return `![${altText}]`;
    },
  );

  // Fix unclosed link syntax [...]
  fixedMarkdown = fixedMarkdown.replace(
    /\[([^\]]*)$/g,
    (match: string, linkText: string): string => {
      return `[${linkText}]`;
    },
  );

  // Fix unclosed images or links missing ")"
  fixedMarkdown = fixedMarkdown.replace(
    /!\[([^\]]*)\]\(([^)]*)$/g,
    (match: string, altText: string, url: string): string => {
      return `![${altText}](${url})`;
    },
  );

  fixedMarkdown = fixedMarkdown.replace(
    /\[([^\]]*)\]\(([^)]*)$/g,
    (match: string, linkText: string, url: string): string => {
      return `[${linkText}](${url})`;
    },
  );

  return fixedMarkdown;
}
