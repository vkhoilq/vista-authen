import { useState } from "react";
import { api } from "@vista-authen/shared";
import type { AccessVerifyResponseGuard, AccessVerifyResponseManager } from "@vista-authen/shared";

interface DashboardProps {
  role: "guard" | "manager";
  token: string;
  onLogout: () => void;
}

export default function Dashboard({ role, token, onLogout }: DashboardProps) {
  const [qrInput, setQrInput] = useState("");
  const [result, setResult] = useState<AccessVerifyResponseGuard | AccessVerifyResponseManager | null>(null);
  const [error, setError] = useState("");

  const handleVerify = async () => {
    setError("");
    setResult(null);

    try {
      const response = await api.post("/api/v1/access/verify", {
        qr_payload: qrInput,
      }, {
        headers: { Authorization: `Bearer ${token}` },
      });
      setResult(response.data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Verification failed");
    }
  };

  return (
    <div style={{ maxWidth: 600, margin: "2rem auto", padding: "0 1rem" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h1>Checker Dashboard</h1>
        <button onClick={onLogout} style={{ padding: "0.5rem 1rem" }}>Logout</button>
      </div>

      <p>Role: <strong>{role}</strong></p>

      <div style={{ marginBottom: "1rem" }}>
        <label htmlFor="qr-input" style={{ display: "block", marginBottom: "0.5rem" }}>
          QR Payload (paste for testing)
        </label>
        <textarea
          id="qr-input"
          value={qrInput}
          onChange={(e) => setQrInput(e.target.value)}
          rows={3}
          style={{ width: "100%", padding: "0.5rem", fontSize: "0.875rem" }}
          placeholder="V1|resident-id|timestamp|signature"
        />
      </div>

      <button
        onClick={handleVerify}
        disabled={!qrInput}
        style={{
          width: "100%",
          padding: "0.75rem",
          fontSize: "1rem",
          cursor: qrInput ? "pointer" : "not-allowed",
          opacity: qrInput ? 1 : 0.5,
        }}
      >
        Verify QR Code
      </button>

      {error && <div style={{ color: "red", marginTop: "1rem" }}>{error}</div>}

      {result && (
        <div
          style={{
            marginTop: "1rem",
            padding: "1rem",
            borderRadius: "4px",
            background: result.status === "valid" ? "#d4edda" : result.status === "expired" ? "#fff3cd" : "#f8d7da",
          }}
        >
          <p style={{ fontSize: "1.5rem", fontWeight: "bold", margin: 0 }}>
            {result.status === "valid" ? "✓ Valid" : result.status === "expired" ? "⏱ Expired" : "✗ Invalid"}
          </p>
          {"resident_name" in result && (
            <>
              <p>Resident: {result.resident_name}</p>
              <p>Unit: {result.unit}</p>
            </>
          )}
        </div>
      )}

      {role === "manager" && (
        <div style={{ marginTop: "2rem" }}>
          <h2>Audit Logs</h2>
          <p style={{ color: "#666" }}>Audit log viewer will be implemented in Phase 6.</p>
        </div>
      )}
    </div>
  );
}
