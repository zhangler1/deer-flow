// SPDX-License-Identifier: MIT

"use client";

import { useCallback, useEffect, useState } from "react";

import { fetchAdmins, addAdmin, type AdminRecord } from "~/core/api/dashboard";

interface AdminManagerDialogProps {
  isDark: boolean;
  onClose: () => void;
}

export function AdminManagerDialog({ isDark, onClose }: AdminManagerDialogProps) {
  const [admins, setAdmins] = useState<AdminRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [newOA, setNewOA] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const loadAdmins = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await fetchAdmins();
      setAdmins(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "加载管理员列表失败");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadAdmins();
  }, [loadAdmins]);

  const handleAdd = useCallback(async () => {
    const oa = newOA.trim();
    if (!oa) return;
    try {
      setSubmitting(true);
      setError(null);
      setSuccess(null);
      await addAdmin(oa);
      setSuccess(`已添加管理员 ${oa}`);
      setNewOA("");
      await loadAdmins();
    } catch (err) {
      setError(err instanceof Error ? err.message : "添加管理员失败");
    } finally {
      setSubmitting(false);
    }
  }, [newOA, loadAdmins]);

  const cardBg = isDark ? "rgb(31,41,55)" : "rgb(255,255,255)";
  const border = isDark ? "rgb(55,65,81)" : "rgb(229,231,235)";
  const textMain = isDark ? "rgb(243,244,246)" : "rgb(17,24,39)";
  const textSub = isDark ? "rgb(156,163,175)" : "rgb(107,114,128)";
  const inputBg = isDark ? "rgb(17,24,39)" : "rgb(255,255,255)";

  return (
    <div
      onClick={onClose}
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 50,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        backgroundColor: "rgba(0,0,0,0.5)",
        padding: "1rem",
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          width: "100%",
          maxWidth: "32rem",
          maxHeight: "80vh",
          overflow: "auto",
          borderRadius: "0.75rem",
          border: `1px solid ${border}`,
          backgroundColor: cardBg,
          padding: "1.5rem",
          boxShadow: "0 10px 25px rgba(0,0,0,0.2)",
        }}
      >
        {/* 标题 */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            marginBottom: "1rem",
          }}
        >
          <h3 style={{ fontSize: "1.125rem", fontWeight: 600, color: textMain }}>
            管理员管理
          </h3>
          <button
            onClick={onClose}
            style={{
              border: "none",
              background: "transparent",
              cursor: "pointer",
              fontSize: "1.25rem",
              lineHeight: 1,
              color: textSub,
            }}
            aria-label="关闭"
          >
            ×
          </button>
        </div>

        {/* 添加表单：显示为 OA，实际提交的是 login_name */}
        <div style={{ display: "flex", gap: "0.5rem", marginBottom: "0.75rem" }}>
          <input
            type="text"
            placeholder="请输入 OA"
            value={newOA}
            onChange={(e) => setNewOA(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") void handleAdd();
            }}
            style={{
              flex: 1,
              borderRadius: "0.375rem",
              border: `1px solid ${border}`,
              backgroundColor: inputBg,
              color: textMain,
              padding: "0.5rem 0.75rem",
              fontSize: "0.875rem",
            }}
          />
          <button
            onClick={() => void handleAdd()}
            disabled={submitting || !newOA.trim()}
            style={{
              borderRadius: "0.375rem",
              border: "none",
              backgroundColor: "rgb(37,99,235)",
              color: "#fff",
              padding: "0.5rem 1rem",
              fontSize: "0.875rem",
              cursor: submitting || !newOA.trim() ? "not-allowed" : "pointer",
              opacity: submitting || !newOA.trim() ? 0.6 : 1,
              whiteSpace: "nowrap",
            }}
          >
            {submitting ? "添加中..." : "添加"}
          </button>
        </div>

        {/* 提示信息 */}
        {error && (
          <div style={{ marginBottom: "0.75rem", fontSize: "0.8125rem", color: "rgb(239,68,68)" }}>
            {error}
          </div>
        )}
        {success && (
          <div style={{ marginBottom: "0.75rem", fontSize: "0.8125rem", color: "rgb(34,197,94)" }}>
            {success}
          </div>
        )}

        {/* 管理员列表（只读，展示 OA 与授予时间） */}
        <div style={{ fontSize: "0.75rem", color: textSub, marginBottom: "0.5rem" }}>
          当前管理员 · OA（{admins.length}）
        </div>
        {loading ? (
          <div style={{ padding: "1rem 0", fontSize: "0.875rem", color: textSub }}>
            加载中...
          </div>
        ) : admins.length === 0 ? (
          <div style={{ padding: "1rem 0", fontSize: "0.875rem", color: textSub }}>
            暂无管理员
          </div>
        ) : (
          <ul style={{ listStyle: "none", margin: 0, padding: 0 }}>
            {admins.map((a) => (
              <li
                key={a.login_name}
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  padding: "0.5rem 0",
                  borderBottom: `1px solid ${border}`,
                }}
              >
                <span style={{ fontSize: "0.875rem", color: textMain }}>
                  {a.login_name}
                </span>
                {a.created_at && (
                  <span style={{ fontSize: "0.6875rem", color: textSub }}>
                    {new Date(a.created_at).toLocaleString()}
                  </span>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
