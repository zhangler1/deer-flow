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
import { X, FileText, Loader2 } from "lucide-react";
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
}

export interface AttachmentUploadRef {
  addFiles: (files: File[]) => void;
  triggerSelect: () => void;
  clear: () => void;
  getSuccessfulAttachments: () => Array<{ filename: string; content: string }>;
}

interface AttachmentUploadProps {
  maxFiles?: number;
  maxSizeMB?: number;
  disabled?: boolean;
  onChange?: (attachments: AttachmentFile[]) => void;
}

const SUPPORTED_EXTENSIONS = new Set([
  "pdf",
  "doc",
  "docx",
  "xls",
  "xlsx",
  "ppt",
  "pptx",
  "txt",
  "md",
  "csv",
  "json",
  "xml",
  "html",
]);

const ACCEPT_STRING = Array.from(SUPPORTED_EXTENSIONS)
  .map((ext) => `.${ext}`)
  .join(",");

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function getFileTypeLabel(filename: string): string {
  const ext = filename.split(".").pop()?.toUpperCase() || "FILE";
  return ext;
}

function getFileIconColor(filename: string): string {
  const ext = filename.split(".").pop()?.toLowerCase() || "";
  if (["pdf"].includes(ext)) return "bg-red-500";
  if (["doc", "docx"].includes(ext)) return "bg-blue-500";
  if (["xls", "xlsx", "csv"].includes(ext)) return "bg-green-500";
  if (["ppt", "pptx"].includes(ext)) return "bg-orange-500";
  if (["txt", "md", "json", "xml", "html"].includes(ext))
    return "bg-gray-500";
  return "bg-slate-500";
}

const AttachmentUpload = forwardRef<AttachmentUploadRef, AttachmentUploadProps>(
  ({ maxFiles = 5, maxSizeMB = 50, disabled = false, onChange }, ref) => {
    const [attachments, setAttachments] = useState<AttachmentFile[]>([]);
    const fileInputRef = useRef<HTMLInputElement>(null);
    const maxSizeBytes = maxSizeMB * 1024 * 1024;

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

    const uploadFile = useCallback(
      async (attachment: AttachmentFile) => {
        updateAttachments((prev) =>
          prev.map((a) =>
            a.id === attachment.id ? { ...a, status: "uploading" as const } : a,
          ),
        );

        try {
          const result = await uploadDocument(attachment.file);
          updateAttachments((prev) =>
            prev.map((a) =>
              a.id === attachment.id
                ? { ...a, status: "success" as const, content: result.content }
                : a,
            ),
          );
        } catch (error) {
          const errorMessage =
            error instanceof Error ? error.message : "Upload failed";
          updateAttachments((prev) =>
            prev.map((a) =>
              a.id === attachment.id
                ? { ...a, status: "error" as const, errorMessage }
                : a,
            ),
          );
          toast.error(`${attachment.name}: ${errorMessage}`);
        }
      },
      [updateAttachments],
    );

    const addFiles = useCallback(
      (files: File[]) => {
        if (disabled) return;

        const newAttachments: AttachmentFile[] = [];

        for (const file of files) {
          if (attachments.length + newAttachments.length >= maxFiles) {
            toast.warning(`Maximum ${maxFiles} files allowed`);
            break;
          }

          if (file.size > maxSizeBytes) {
            toast.warning(
              `${file.name} is too large (max ${maxSizeMB}MB)`,
            );
            continue;
          }

          const ext = file.name.split(".").pop()?.toLowerCase() || "";
          if (!SUPPORTED_EXTENSIONS.has(ext)) {
            toast.warning(
              `${file.name}: unsupported file type (.${ext})`,
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
          };
          newAttachments.push(attachment);
        }

        if (newAttachments.length > 0) {
          updateAttachments((prev) => [...prev, ...newAttachments]);
          // Start uploading each file
          for (const attachment of newAttachments) {
            uploadFile(attachment);
          }
        }
      },
      [
        attachments.length,
        disabled,
        maxFiles,
        maxSizeBytes,
        maxSizeMB,
        updateAttachments,
        uploadFile,
      ],
    );

    const removeAttachment = useCallback(
      (id: string) => {
        updateAttachments((prev) => prev.filter((a) => a.id !== id));
      },
      [updateAttachments],
    );

    const triggerSelect = useCallback(() => {
      if (disabled) return;
      fileInputRef.current?.click();
    }, [disabled]);

    const clear = useCallback(() => {
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
        <div className="flex flex-wrap gap-2 px-3 pt-2 pb-1">
          {attachments.map((attachment) => (
            <div
              key={attachment.id}
              className={cn(
                "relative flex items-center gap-2.5 rounded-lg border px-2.5 py-2 pr-8",
                "max-w-[240px] min-w-[140px] cursor-default",
                "bg-background transition-colors",
                attachment.status === "error" &&
                  "border-destructive/50 bg-destructive/5",
                attachment.status === "uploading" && "border-primary/30",
                attachment.status === "success" && "border-border",
              )}
            >
              {/* File icon */}
              <div
                className={cn(
                  "flex h-8 w-8 shrink-0 items-center justify-center rounded",
                  getFileIconColor(attachment.name),
                )}
              >
                {attachment.status === "uploading" ? (
                  <Loader2 className="h-4 w-4 animate-spin text-white" />
                ) : (
                  <FileText className="h-4 w-4 text-white" />
                )}
              </div>

              {/* File info */}
              <div className="flex min-w-0 flex-1 flex-col gap-0.5">
                <div className="truncate text-xs font-medium text-foreground">
                  {attachment.name}
                </div>
                <div className="text-[11px] text-muted-foreground whitespace-nowrap">
                  {getFileTypeLabel(attachment.name)}
                  &nbsp;&middot;&nbsp;
                  {formatFileSize(attachment.size)}
                  {attachment.status === "uploading" && (
                    <span className="ml-1 text-primary">parsing...</span>
                  )}
                  {attachment.status === "error" && (
                    <span className="ml-1 text-destructive">failed</span>
                  )}
                </div>
              </div>

              {/* Remove button */}
              <button
                type="button"
                className={cn(
                  "absolute top-1 right-1.5 flex h-[18px] w-[18px] items-center justify-center",
                  "rounded-full bg-black/15 text-white text-[11px] leading-none",
                  "cursor-pointer transition-colors hover:bg-black/35",
                )}
                onClick={() => removeAttachment(attachment.id)}
                aria-label="Remove attachment"
              >
                <X className="h-3 w-3" />
              </button>
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
