// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

"use client";

import React, {
  forwardRef,
  useCallback,
  useEffect,
  useImperativeHandle,
  useRef,
  useState,
} from "react";
import { X, Loader2, CheckCircle2, AlertCircle } from "lucide-react";
import { toast } from "sonner";

import { uploadDocument } from "~/core/api/documents";
import { cn } from "~/lib/utils";

export interface AttachmentFile {
  id: string;
  file: File;
  name: string;
  size: number;
  type: string;
  status: "pending" | "uploading" | "success" | "error";
  content?: string;
  errorMessage?: string;
  progress?: number;
}

export interface AttachmentUploadRef {
  addFiles: (files: File[]) => void;
  triggerSelect: () => void;
  clear: () => void;
  getSuccessfulAttachments: () => Array<{ filename: string; content: string }>;
}

interface AttachmentUploadProps {
  maxFiles?: number;
  /** 默认最大文件大小（MB），当文件类型没有单独限制时使用 */
  maxSizeMB?: number;
  /** 按文件扩展名单独限制大小（MB），示例：{ pdf: 10, docx: 5 } */
  typeSizeLimits?: Record<string, number>;
  disabled?: boolean;
  onChange?: (attachments: AttachmentFile[]) => void;
}

const SUPPORTED_EXTENSIONS = new Set([
  "pdf",
  "docx",
  "xlsx",
  "pptx",
  "txt",
  "md",
  "csv",
  "json",
  "html",
]);

/** 禁止上传的文件类型（会提示用户不可上传） */
const FORBIDDEN_EXTENSIONS = new Set([
  "doc",
  "xls",
  "xml",
  "ppt",
]);

const ACCEPT_STRING = Array.from(SUPPORTED_EXTENSIONS)
  .map((ext) => `.${ext}`)
  .join(",");

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

/** 返回禁止类型的替代建议格式 */
function getAlternativeExt(forbiddenExt: string): string {
  const altMap: Record<string, string> = {
    doc: "docx",
    xls: "xlsx",
    ppt: "pptx",
    xml: "json",
  };
  return altMap[forbiddenExt] || forbiddenExt;
}

function getFileTypeLabel(filename: string): string {
  const ext = filename.split(".").pop()?.toLowerCase() || "";
  const typeMap: Record<string, string> = {
    pdf: "PDF",
    doc: "Word",
    docx: "Word",
    xls: "Excel",
    xlsx: "Excel",
    ppt: "PPT",
    pptx: "PPT",
    txt: "Text",
    md: "Markdown",
    csv: "CSV",
    json: "JSON",
    xml: "XML",
    html: "HTML",
  };
  return typeMap[ext] || ext.toUpperCase() || "FILE";
}

function getFileStatusText(status: AttachmentFile["status"]): string {
  switch (status) {
    case "pending":
      return "等待上传";
    case "uploading":
      return "解析中...";
    case "success":
      return "上传成功";
    case "error":
      return "上传失败";
  }
}

/** 将多个扩展名归并为一类显示（如 doc,docx → Word文档） */
export function getTypeSizeSummary(
  typeSizeLimits?: Record<string, number>,
  defaultMaxMB?: number,
): string {
  if (!typeSizeLimits || Object.keys(typeSizeLimits).length === 0) {
    return `单个文件最大 ${defaultMaxMB ?? 2}MB`;
  }

  // 按文件类型标签归并
  const seen = new Set<string>();
  const groups: { label: string; size: number }[] = [];
  for (const [ext, size] of Object.entries(typeSizeLimits)) {
    const label = getFileTypeLabel(`file.${ext}`);
    const key = `${label}:${size}`;
    if (!seen.has(key)) {
      seen.add(key);
      groups.push({ label, size });
    }
  }

  const parts = groups.map((g) => `${g.label}≤${g.size}MB`);
  if (defaultMaxMB !== undefined) {
    parts.push(`其他≤${defaultMaxMB}MB`);
  }
  return parts.join("、");
}

/** 文件类型图标 SVG 组件 */
function FileTypeIcon({ filename, className }: { filename: string; className?: string }) {
  const ext = filename.split(".").pop()?.toLowerCase() || "";

  // 根据文件类型返回不同颜色的图标
  const getGradient = () => {
    if (["doc", "docx"].includes(ext))
      return { from: "#44ADFE", to: "#5580FF", letter: "W" };
    if (["pdf"].includes(ext))
      return { from: "#FF6B6B", to: "#EE5A24", letter: "P" };
    if (["xls", "xlsx", "csv"].includes(ext))
      return { from: "#2ED573", to: "#17A558", letter: "X" };
    if (["ppt", "pptx"].includes(ext))
      return { from: "#FF9F43", to: "#EE5A24", letter: "P" };
    if (["txt", "md"].includes(ext))
      return { from: "#A4B0BE", to: "#747D8C", letter: "T" };
    if (["json", "xml", "html"].includes(ext))
      return { from: "#5F27CD", to: "#341F97", letter: "<>" };
    return { from: "#A4B0BE", to: "#747D8C", letter: "F" };
  };

  const { from, to, letter } = getGradient();
  const gradientId = `file-icon-gradient-${ext}`;

  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width="1em"
      height="1em"
      fill="none"
      viewBox="0 0 32 32"
      className={className}
    >
      <defs>
        <linearGradient id={gradientId} x1="25" x2="3.556" y1="27" y2="22.867" gradientUnits="userSpaceOnUse">
          <stop stopColor={from} />
          <stop offset="1" stopColor={to} />
        </linearGradient>
      </defs>
      <path
        fill={`url(#${gradientId})`}
        d="M7.283 6.42C7 6.976 7 7.704 7 9.16v13.68c0 1.456 0 2.184.283 2.74a2.6 2.6 0 0 0 1.137 1.137C8.976 27 9.704 27 11.16 27h9.68c1.456 0 2.184 0 2.74-.283a2.6 2.6 0 0 0 1.137-1.137c.283-.556.283-1.284.283-2.74V11l-6-6h-7.84c-1.456 0-2.184 0-2.74.283A2.6 2.6 0 0 0 7.283 6.42"
      />
      <path
        fill="#fff"
        fillOpacity="0.55"
        d="m19 5 6 6h-1.84c-1.456 0-2.184 0-2.74-.283a2.6 2.6 0 0 1-1.137-1.137C19 9.024 19 8.296 19 6.84z"
      />
      <text
        x="16"
        y="21"
        textAnchor="middle"
        fill="#19205A"
        fontSize="8"
        fontWeight="bold"
        fontFamily="sans-serif"
      >
        {letter}
      </text>
    </svg>
  );
}

/** 上传进度条组件 */
function UploadProgressBar({ progress, status }: { progress: number; status: AttachmentFile["status"] }) {
  if (status !== "uploading" && status !== "pending") return null;

  return (
    <div className="absolute bottom-0 left-0 right-0 h-[3px] overflow-hidden rounded-b-[10px]">
      <div className="h-full w-full bg-[#e8f0fe] dark:bg-[#102030]" />
      <div
        className={cn(
          "absolute top-0 left-0 h-full rounded-full transition-all duration-300 ease-out",
          status === "uploading"
            ? "bg-gradient-to-r from-blue-400 to-blue-600 animate-pulse"
            : "bg-[#aad0ff] dark:bg-[#225080]",
        )}
        style={{ width: `${progress}%` }}
      />
    </div>
  );
}

const AttachmentUpload = forwardRef<AttachmentUploadRef, AttachmentUploadProps>(
  ({ maxFiles = 2, maxSizeMB = 2, typeSizeLimits, disabled = false, onChange }, ref) => {
    const [attachments, setAttachments] = useState<AttachmentFile[]>([]);
    const fileInputRef = useRef<HTMLInputElement>(null);
    const progressTimerRef = useRef<Map<string, NodeJS.Timeout>>(new Map());
    const maxSizeBytes = maxSizeMB * 1024 * 1024;

    /** 获取指定扩展名对应的最大文件大小（字节） */
    const getFileMaxSize = useCallback(
      (ext: string): { bytes: number; mb: number; custom: boolean } => {
        if (typeSizeLimits && typeSizeLimits[ext] !== undefined) {
          const mb = typeSizeLimits[ext]!;
          return { bytes: mb * 1024 * 1024, mb, custom: true };
        }
        return { bytes: maxSizeBytes, mb: maxSizeMB, custom: false };
      },
      [maxSizeBytes, maxSizeMB, typeSizeLimits],
    );

    const updateAttachments = useCallback(
      (updater: (prev: AttachmentFile[]) => AttachmentFile[]) => {
        setAttachments(updater);
      },
      [],
    );

    // Notify parent of attachment changes after render (avoids setState-during-render)
    useEffect(() => {
      onChange?.(attachments);
    }, [attachments, onChange]);

    // Cleanup progress timers on unmount
    useEffect(() => {
      return () => {
        progressTimerRef.current.forEach((timer) => clearInterval(timer));
        progressTimerRef.current.clear();
      };
    }, []);

    // Simulate progress animation
    const startProgressSimulation = useCallback(
      (attachmentId: string) => {
        // Clear existing timer if any
        const existing = progressTimerRef.current.get(attachmentId);
        if (existing) clearInterval(existing);

        const timer = setInterval(() => {
          setAttachments((prev) => {
            const attachment = prev.find((a) => a.id === attachmentId);
            if (!attachment || attachment.status !== "uploading") {
              clearInterval(timer);
              progressTimerRef.current.delete(attachmentId);
              return prev;
            }
            const currentProgress = attachment.progress || 0;
            // Slow down as it approaches 90%, never reach 100% until actually done
            if (currentProgress >= 90) {
              return prev;
            }
            const increment = currentProgress < 60 ? 8 : currentProgress < 80 ? 3 : 1;
            return prev.map((a) =>
              a.id === attachmentId
                ? { ...a, progress: Math.min(90, currentProgress + increment) }
                : a,
            );
          });
        }, 300);

        progressTimerRef.current.set(attachmentId, timer);
      },
      [],
    );

    const uploadFile = useCallback(
      async (attachment: AttachmentFile) => {
        updateAttachments((prev) =>
          prev.map((a) =>
            a.id === attachment.id
              ? { ...a, status: "uploading" as const, progress: 5 }
              : a,
          ),
        );

        startProgressSimulation(attachment.id);

        try {
          const result = await uploadDocument(attachment.file);
          // Clear progress timer
          const timer = progressTimerRef.current.get(attachment.id);
          if (timer) {
            clearInterval(timer);
            progressTimerRef.current.delete(attachment.id);
          }
          updateAttachments((prev) =>
            prev.map((a) =>
              a.id === attachment.id
                ? { ...a, status: "success" as const, content: result.content, progress: 100 }
                : a,
            ),
          );
        } catch (error) {
          // Clear progress timer
          const timer = progressTimerRef.current.get(attachment.id);
          if (timer) {
            clearInterval(timer);
            progressTimerRef.current.delete(attachment.id);
          }
          const errorMessage =
            error instanceof Error ? error.message : "Upload failed";
          updateAttachments((prev) =>
            prev.map((a) =>
              a.id === attachment.id
                ? { ...a, status: "error" as const, errorMessage, progress: 0 }
                : a,
            ),
          );
          toast.error(`${attachment.name}: ${errorMessage}`);
        }
      },
      [updateAttachments, startProgressSimulation],
    );

    const addFiles = useCallback(
      (files: File[]) => {
        if (disabled) return;

        const newAttachments: AttachmentFile[] = [];
        const oversizedAttachments: AttachmentFile[] = [];

        for (const file of files) {
          if (attachments.length + newAttachments.length + oversizedAttachments.length >= maxFiles) {
            toast.warning(`最多允许上传 ${maxFiles} 个文件`);
            break;
          }

          const ext = file.name.split(".").pop()?.toLowerCase() || "";
          // 禁止上传的类型单独提示
          if (FORBIDDEN_EXTENSIONS.has(ext)) {
            toast.warning(
              `${file.name}: 暂不支持上传 .${ext} 格式文件，请转换为 .${getAlternativeExt(ext)} 格式后上传`,
            );
            continue;
          }
          if (!SUPPORTED_EXTENSIONS.has(ext)) {
            toast.warning(
              `${file.name}: 不支持的文件类型 (.${ext})`,
            );
            continue;
          }

          const attachment: AttachmentFile = {
            id: `${Date.now()}-${Math.random().toString(36).slice(2)}`,
            file,
            name: file.name,
            size: file.size,
            type: file.type || ext,
            status: "pending",
            progress: 0,
          };

          const sizeLimit = getFileMaxSize(ext);
          if (file.size > sizeLimit.bytes) {
            // Mark as error immediately, show in list with error state
            attachment.status = "error";
            attachment.errorMessage = `文件过大（最大 ${sizeLimit.mb}MB）`;
            oversizedAttachments.push(attachment);
            toast.error(`${file.name} 文件过大（${getFileTypeLabel(file.name)} 类最大 ${sizeLimit.mb}MB）`);
          } else {
            newAttachments.push(attachment);
          }
        }

        // Add all attachments (normal + oversized) to the list
        const allNew = [...newAttachments, ...oversizedAttachments];
        if (allNew.length > 0) {
          updateAttachments((prev) => [...prev, ...allNew]);
          // Only start uploading valid files
          for (const attachment of newAttachments) {
            uploadFile(attachment);
          }
        }
      },
      [
        attachments.length,
        disabled,
        maxFiles,
        maxSizeMB,
        updateAttachments,
        uploadFile,
        getFileMaxSize,
      ],
    );

    const removeAttachment = useCallback(
      (id: string) => {
        // Clear progress timer if running
        const timer = progressTimerRef.current.get(id);
        if (timer) {
          clearInterval(timer);
          progressTimerRef.current.delete(id);
        }
        updateAttachments((prev) => prev.filter((a) => a.id !== id));
      },
      [updateAttachments],
    );

    const triggerSelect = useCallback(() => {
      if (disabled) return;
      fileInputRef.current?.click();
    }, [disabled]);

    const clear = useCallback(() => {
      // Clear all progress timers
      progressTimerRef.current.forEach((timer) => clearInterval(timer));
      progressTimerRef.current.clear();
      updateAttachments(() => []);
    }, [updateAttachments]);

    const getSuccessfulAttachments = useCallback(() => {
      return attachments
        .filter((a) => a.status === "success" && a.content)
        .map((a) => ({ filename: a.name, content: a.content! }));
    }, [attachments]);

    useImperativeHandle(ref, () => ({
      addFiles,
      triggerSelect,
      clear,
      getSuccessfulAttachments,
    }));

    const handleFileSelect = useCallback(
      (event: React.ChangeEvent<HTMLInputElement>) => {
        const files = event.target.files;
        if (!files) return;
        addFiles(Array.from(files));
        event.target.value = "";
      },
      [addFiles],
    );

    return (
      <div className="w-full">
        {/* Hidden file input - always rendered so triggerSelect works */}
        <input
          ref={fileInputRef}
          type="file"
          accept={ACCEPT_STRING}
          multiple
          className="hidden"
          onChange={handleFileSelect}
        />

        {/* Attachment list */}
        {attachments.length > 0 && (
        <div className="flex flex-wrap gap-2.5 px-3 pt-3 pb-1">
          {attachments.map((attachment) => (
            <div
              key={attachment.id}
              className={cn(
                "group relative flex items-center gap-2.5 rounded-[10px] border px-2.5 py-2 pr-7",
                "w-[200px] cursor-default overflow-hidden",
                "bg-muted/40 transition-all duration-200",
                attachment.status === "error" &&
                  "border-[rgba(235,87,87,0.5)] bg-[rgba(235,87,87,0.06)] dark:border-[rgba(248,113,113,0.5)] dark:bg-[rgba(248,113,113,0.08)]",
                attachment.status === "uploading" &&
                  "border-[#cce0ff] bg-[#f0f4fd] dark:border-[#1a4060] dark:bg-[#0e1825]",
                attachment.status === "success" && "border-border hover:border-border/80",
                attachment.status === "pending" && "border-border/50 opacity-70",
              )}
            >
              {/* File type icon */}
              <div className="flex h-9 w-9 shrink-0 items-center justify-center">
                {attachment.status === "uploading" ? (
                  <div className="relative flex h-9 w-9 items-center justify-center">
                    <Loader2 className="h-6 w-6 animate-spin text-primary" />
                  </div>
                ) : (
                  <FileTypeIcon filename={attachment.name} className="text-[36px]" />
                )}
              </div>

              {/* File info */}
              <div className="flex min-w-0 flex-1 flex-col gap-0.5">
                {/* File title/name */}
                <div className="truncate text-xs font-medium leading-[14px] text-foreground">
                  {attachment.name}
                </div>
                {/* File type + size + status */}
                <div className="mt-0.5 flex items-center gap-0 text-[11px] leading-[14px] text-muted-foreground">
                  <span>{getFileTypeLabel(attachment.name)}</span>
                  <span className="select-none">&nbsp;·&nbsp;</span>
                  <span>{formatFileSize(attachment.size)}</span>
                </div>
                {/* Status indicator */}
                {attachment.status !== "success" && (
                  <div className="mt-0.5 flex items-center gap-1 text-[10px] leading-[12px]">
                    {attachment.status === "uploading" && (
                      <span className="text-primary font-medium animate-pulse">
                        {getFileStatusText(attachment.status)}
                      </span>
                    )}
                    {attachment.status === "error" && (
                      <span className="text-destructive flex items-center gap-0.5">
                        <AlertCircle className="h-2.5 w-2.5" />
                        {attachment.errorMessage || getFileStatusText(attachment.status)}
                      </span>
                    )}
                    {attachment.status === "pending" && (
                      <span className="text-muted-foreground">
                        {getFileStatusText(attachment.status)}
                      </span>
                    )}
                  </div>
                )}
                {/* Success indicator (compact) */}
                {attachment.status === "success" && (
                  <div className="mt-0.5 flex items-center gap-0.5 text-[10px] leading-[12px] text-green-600">
                    <CheckCircle2 className="h-2.5 w-2.5" />
                    <span>{getFileStatusText(attachment.status)}</span>
                  </div>
                )}
              </div>

              {/* Remove button - visible on hover */}
              <button
                type="button"
                className={cn(
                  "absolute top-1 right-1 flex h-[16px] w-[16px] items-center justify-center",
                  "rounded-full bg-black/60 text-white opacity-0 transition-opacity",
                  "cursor-pointer group-hover:opacity-100 hover:bg-black/80",
                )}
                onClick={() => removeAttachment(attachment.id)}
                aria-label="移除附件"
              >
                <X className="h-2.5 w-2.5" />
              </button>

              {/* Progress bar */}
              <UploadProgressBar
                progress={attachment.progress || 0}
                status={attachment.status}
              />
            </div>
          ))}
        </div>
        )}
      </div>
    );
  },
);

AttachmentUpload.displayName = "AttachmentUpload";

export default AttachmentUpload;
