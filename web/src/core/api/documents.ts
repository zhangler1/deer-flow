// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

import { resolveServiceURL } from "./resolve-service-url";

export interface DocumentUploadResponse {
  id: string;
  filename: string;
  content: string;
  size: number;
  file_type: string;
}

/**
 * Upload a document file to the backend for parsing.
 * The backend will call Easyparse to convert the file to text.
 */
export async function uploadDocument(
  file: File,
  options: { signal?: AbortSignal } = {},
): Promise<DocumentUploadResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(resolveServiceURL("documents/upload"), {
    method: "POST",
    body: formData,
    signal: options.signal,
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    const detail = errorData.detail || `Upload failed with status ${response.status}`;
    throw new Error(detail);
  }

  return response.json();
}
