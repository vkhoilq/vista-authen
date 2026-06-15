import { useState, useEffect, useCallback } from "react";
import { api } from "@vista-authen/shared";
import type { AuditLogRead } from "@vista-authen/shared";

interface AuditLogViewerProps {
  // token: string; — reserved for future auth customization
}

export default function AuditLogViewer(_props: AuditLogViewerProps) {
  const [logs, setLogs] = useState<AuditLogRead[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [page, setPage] = useState(1);
  const [actionFilter, setActionFilter] = useState("");

  const fetchLogs = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const params: Record<string, string | number> = { page, page_size: 20 };
      if (actionFilter) params.action = actionFilter;

      const response = await api.get("/api/v1/audit-logs", { params });
      setLogs(response.data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load audit logs");
    } finally {
      setLoading(false);
    }
  }, [page, actionFilter]);

  useEffect(() => {
    fetchLogs();
  }, [fetchLogs]);

  const actionOptions = [
    { value: "", label: "All actions" },
    { value: "scan_success", label: "Scan success" },
    { value: "scan_failed_expired", label: "Scan expired" },
    { value: "scan_failed_bad_signature", label: "Bad signature" },
    { value: "registration_blocked", label: "Registration blocked" },
    { value: "device_activated", label: "Device activated" },
    { value: "device_revoked", label: "Device revoked" },
    { value: "resident_provisioned", label: "Resident provisioned" },
  ];

  return (
    <div>
      <div style={{ display: "flex", gap: "0.5rem", marginBottom: "1rem", alignItems: "center" }}>
        <select
          value={actionFilter}
          onChange={(e) => { setActionFilter(e.target.value); setPage(1); }}
          style={{ padding: "0.4rem", fontSize: "0.875rem" }}
        >
          {actionOptions.map((opt) => (
            <option key={opt.value} value={opt.value}>{opt.label}</option>
          ))}
        </select>
        <button onClick={fetchLogs} disabled={loading} style={{ padding: "0.4rem 0.75rem", fontSize: "0.875rem" }}>
          {loading ? "Loading..." : "Refresh"}
        </button>
      </div>

      {error && <div style={{ color: "red", marginBottom: "0.5rem" }}>{error}</div>}

      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.8rem" }}>
        <thead>
          <tr style={{ textAlign: "left", borderBottom: "2px solid #ddd" }}>
            <th style={{ padding: "0.4rem" }}>Time</th>
            <th style={{ padding: "0.4rem" }}>Action</th>
            <th style={{ padding: "0.4rem" }}>Actor</th>
            <th style={{ padding: "0.4rem" }}>Unit</th>
          </tr>
        </thead>
        <tbody>
          {logs.map((log) => (
            <tr key={log.id} style={{ borderBottom: "1px solid #eee" }}>
              <td style={{ padding: "0.4rem" }}>
                {new Date(log.timestamp).toLocaleString()}
              </td>
              <td style={{ padding: "0.4rem" }}>
                <code style={{ fontSize: "0.75rem" }}>{log.action}</code>
              </td>
              <td style={{ padding: "0.4rem" }}>{log.actor_role || "-"}</td>
              <td style={{ padding: "0.4rem" }}>{log.unit_id ? log.unit_id.slice(0, 8) : "-"}</td>
            </tr>
          ))}
          {logs.length === 0 && !loading && (
            <tr>
              <td colSpan={4} style={{ padding: "1rem", textAlign: "center", color: "#888" }}>
                No logs found
              </td>
            </tr>
          )}
        </tbody>
      </table>

      <div style={{ marginTop: "0.75rem", display: "flex", gap: "0.5rem", justifyContent: "center" }}>
        <button onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page <= 1} style={{ padding: "0.3rem 0.75rem" }}>
          ← Prev
        </button>
        <span style={{ padding: "0.3rem" }}>Page {page}</span>
        <button onClick={() => setPage((p) => p + 1)} disabled={logs.length < 20} style={{ padding: "0.3rem 0.75rem" }}>
          Next →
        </button>
      </div>
    </div>
  );
}