// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

"use client";

import Mention from "@tiptap/extension-mention";
import { Editor, Extension, type Content } from "@tiptap/react";
import {
  EditorContent,
  type EditorInstance,
  EditorRoot,
  type JSONContent,
  StarterKit,
  Placeholder,
} from "novel";
import { Markdown } from "tiptap-markdown";
import { useDebouncedCallback } from "use-debounce";
import { useTranslations } from "next-intl";

import "~/styles/prosemirror.css";
import { resourceSuggestion } from "./resource-suggestion";
import React, { forwardRef, useEffect, useMemo, useRef } from "react";
import type { Resource } from "~/core/messages";
import { LoadingOutlined } from "@ant-design/icons";
import type { DeerFlowConfig } from "~/core/config";

export interface MessageInputRef {
  focus: () => void;
  submit: () => void;
  setContent: (content: string) => void;
}

export interface MessageInputProps {
  className?: string;
  placeholder?: string;
  loading?: boolean;
  config?: DeerFlowConfig | null;
  onChange?: (markdown: string) => void;
  onEnter?: (message: string, resources: Array<Resource>) => void;
  maxLength?: number;
  disableSubmit?: boolean;
}

function formatMessage(content: JSONContent) {
  if (content.content) {
    const output: {
      text: string;
      resources: Array<Resource>;
    } = {
      text: "",
      resources: [],
    };
    for (const node of content.content) {
      const { text, resources } = formatMessage(node);
      output.text += text;
      output.resources.push(...resources);
    }
    return output;
  } else {
    return formatItem(content);
  }
}

function formatItem(item: JSONContent): {
  text: string;
  resources: Array<Resource>;
} {
  if (item.type === "text") {
    return { text: item.text ?? "", resources: [] };
  }
  if (item.type === "mention") {
    return {
      text: `[${item.attrs?.label}](${item.attrs?.id})`,
      resources: [
        { uri: item.attrs?.id ?? "", title: item.attrs?.label ?? "" },
      ],
    };
  }
  return { text: "", resources: [] };
}

/** 遍历 ProseMirror doc 只统计文本节点字符数，与 formatMessage 的计数方式一致 */
function countDocTextChars(doc: any): number {
  let count = 0;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  doc.descendants((node: any) => {
    if (node.isText) {
      count += (node.text ?? "").length;
    }
  });
  return count;
}

/** 递归计算 JSONContent 树的纯文本字符数 */
function getNodeTextLength(node: JSONContent): number {
  if (node.type === "text") {
    return (node.text ?? "").length;
  }
  if (node.content) {
    return node.content.reduce((sum, child) => sum + getNodeTextLength(child), 0);
  }
  return 0;
}

/** 递归截断 JSONContent 树，保留前 maxLength 个字符 */
function truncateContent(content: JSONContent, maxLength: number): JSONContent {
  if (!content.content) return content;
  let remaining = maxLength;
  const truncatedNodes: JSONContent[] = [];
  for (const node of content.content) {
    if (remaining <= 0) break;
    const nodeLen = getNodeTextLength(node);
    if (nodeLen <= remaining) {
      truncatedNodes.push(node);
      remaining -= nodeLen;
    } else {
      truncatedNodes.push(truncateSingleNode(node, remaining));
      remaining = 0;
      break;
    }
  }
  return { ...content, content: truncatedNodes };
}

function truncateSingleNode(node: JSONContent, maxLength: number): JSONContent {
  if (node.type === "text") {
    return { ...node, text: (node.text ?? "").slice(0, maxLength) };
  }
  if (node.content) {
    let remaining = maxLength;
    const truncatedChildren: JSONContent[] = [];
    for (const child of node.content) {
      if (remaining <= 0) break;
      const childLen = getNodeTextLength(child);
      if (childLen <= remaining) {
        truncatedChildren.push(child);
        remaining -= childLen;
      } else {
        truncatedChildren.push(truncateSingleNode(child, remaining));
        remaining = 0;
        break;
      }
    }
    return { ...node, content: truncatedChildren };
  }
  return node;
}

const MessageInput = forwardRef<MessageInputRef, MessageInputProps>(
  (
    { className, loading, config, onChange, onEnter, maxLength = Infinity, disableSubmit = false }: MessageInputProps,
    ref,
  ) => {
    const t = useTranslations("messageInput");
    const editorRef = useRef<Editor>(null);
    const handleEnterRef = useRef<
      ((message: string, resources: Array<Resource>) => void) | undefined
    >(onEnter);
    const disableSubmitRef = useRef(disableSubmit);
    useEffect(() => {
      disableSubmitRef.current = disableSubmit;
    }, [disableSubmit]);
    const debouncedUpdates = useDebouncedCallback(
      async (editor: EditorInstance) => {
        if (onChange) {
          const { text } = formatMessage(editor.getJSON() ?? []);
          onChange(text);
        }
      },
      200,
    );

    const maxLengthRef = useRef(maxLength);
    useEffect(() => {
      maxLengthRef.current = maxLength;
    }, [maxLength]);

    const removeCompositionListenerRef = useRef<(() => void) | null>(null);
    useEffect(() => {
      return () => {
        removeCompositionListenerRef.current?.();
      };
    }, []);

    React.useImperativeHandle(ref, () => ({
      focus: () => {
        editorRef.current?.view.focus();
      },
      submit: () => {
        if (disableSubmitRef.current) return;
        if (onEnter) {
          const { text, resources } = formatMessage(
            editorRef.current?.getJSON() ?? [],
          );
          onEnter(text.slice(0, maxLengthRef.current), resources);
        }
        editorRef.current?.commands.clearContent();
      },
      setContent: (content: string) => {
        if (editorRef.current) {
          editorRef.current.commands.setContent(content);
        }
      },
    }));

    useEffect(() => {
      handleEnterRef.current = onEnter;
    }, [onEnter]);

    const extensions = useMemo(() => {
      const extensions = [
        StarterKit,
        Markdown.configure({
          html: true,
          tightLists: true,
          tightListClass: "tight",
          bulletListMarker: "-",
          linkify: false,
          breaks: false,
          transformPastedText: false,
          transformCopiedText: false,
        }),
        Placeholder.configure({
          showOnlyCurrent: false,
          placeholder: config?.rag.provider ? t("placeholderWithRag") : t("placeholder"),
          emptyEditorClass: "placeholder",
        }),
        Extension.create({
          name: "keyboardHandler",
          addKeyboardShortcuts() {
            return {
              Enter: () => {
                if (disableSubmitRef.current) return false;
                if (handleEnterRef.current) {
                  const { text, resources } = formatMessage(
                    this.editor.getJSON() ?? [],
                  );
                  handleEnterRef.current(
                    text.slice(0, maxLengthRef.current),
                    resources,
                  );
                }
                return this.editor.commands.clearContent();
              },
            };
          },
        }),
      ];
      if (config?.rag.provider) {
        extensions.push(
          Mention.configure({
            HTMLAttributes: {
              class: "mention",
            },
            suggestion: resourceSuggestion,
          }) as Extension,
        );
      }
      return extensions;
    }, [config]);

    if (loading) {
      return (
        <div className={className}>
          <LoadingOutlined />
        </div>
      );
    }

    return (
      <div className={className}>
        <EditorRoot>
          <EditorContent
            immediatelyRender={false}
            extensions={extensions}
            className="border-muted h-full w-full overflow-auto break-words"
            editorProps={{
              attributes: {
                class:
                  "prose prose-base dark:prose-invert inline-editor font-default focus:outline-none max-w-full",
              },
              transformPastedHTML: transformPastedHTML,
              handleTextInput: (view, _from, _to, _text) => {
                if (!maxLengthRef.current || maxLengthRef.current === Infinity) return false;
                // 输入法组合输入期间不拦截，等 compositionend 后由 onUpdate 统一截断
                if (view.composing) return false;
                const charCount = countDocTextChars(view.state.doc);
                if (charCount >= maxLengthRef.current) {
                  return true; // 已达上限，阻止本次文本插入
                }
                return false;
              },
              handlePaste: (view, event) => {
                if (!maxLengthRef.current || maxLengthRef.current === Infinity) return false;

                const clipboardText = event.clipboardData?.getData("text/plain");
                if (!clipboardText) return false;

                const docLen = countDocTextChars(view.state.doc);
                const maxLen = maxLengthRef.current;

                // 已到达上限，直接阻止粘贴
                if (docLen >= maxLen) {
                  event.preventDefault();
                  return true;
                }

                // 计算选中区域实际文本字符数
                const { from, to } = view.state.selection;
                let selectedLen = 0;
                view.state.doc.nodesBetween(from, Math.min(to, view.state.doc.content.size), (node: any) => {
                  if (node.isText) {
                    const start = Math.max(from, node.pos);
                    const end = Math.min(to, node.pos + node.text.length);
                    if (end > start) selectedLen += end - start;
                  }
                });
                const willBe = docLen - selectedLen + clipboardText.length;

                if (willBe <= maxLen) {
                  // 粘贴后不超过限制，不干预
                  return false;
                }

                // 需要截断
                event.preventDefault();
                const available = maxLen - (docLen - selectedLen);
                if (available > 0) {
                  const truncated = clipboardText.slice(0, available);
                  view.dispatch(view.state.tr.insertText(truncated, from, to));
                }
                return true;
              },
            }}
            onCreate={({ editor }) => {
              editorRef.current = editor;
              if (!maxLengthRef.current || maxLengthRef.current === Infinity) return;
              const handleCompositionEnd = () => {
                if (!maxLengthRef.current || maxLengthRef.current === Infinity) return;
                const json = editor.getJSON();
                if (!json) return;
                const { text } = formatMessage(json);
                if (text.length > maxLengthRef.current) {
                  const truncated = truncateContent(json, maxLengthRef.current);
                  // emitUpdate 默认为 false，不会再次触发 onUpdate
                  editor.commands.setContent(truncated);
                  onChange?.(text.slice(0, maxLengthRef.current));
                }
              };
              editor.view.dom.addEventListener('compositionend', handleCompositionEnd);
              removeCompositionListenerRef.current = () => {
                editor.view.dom.removeEventListener('compositionend', handleCompositionEnd);
              };
            }}
            onUpdate={({ editor }) => {
              const { text } = formatMessage(editor.getJSON() ?? []);
              if (text.length > maxLengthRef.current) {
                onChange?.(text.slice(0, maxLengthRef.current));
                return;
              }
              debouncedUpdates(editor);
            }}
          ></EditorContent>
        </EditorRoot>
      </div>
    );
  },
);

function transformPastedHTML(html: string) {
  try {
    const tempEl = document.createElement("div");
    tempEl.innerHTML = html;

    return tempEl.textContent || tempEl.innerText || "";
  } catch (error) {
    console.error("Error transforming pasted HTML", error);

    return "";
  }
}

export default MessageInput;
