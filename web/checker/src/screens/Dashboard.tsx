import { useState } from "react";
import { api } from "@vista-authen/shared";
import type { AccessVerifyResponse } from "@vista-authen/shared";
import { isManagerResponse } from "@vista-authen/shared";
import QRScanner from "../components/QRScanner";
import AuditLogViewer from "../components/AuditLogViewer";

interface DashboardProps {
  role: "guard" | "manager";
  token: string;
  onLogout: () => void;
}

export default function Dashboard({ role, onLogout }: DashboardProps) {
  const [qrInput, setQrInput] = useState("");
  const [result, setResult] = useState<AccessVerifyResponse | null>(null);
  const [error, setError] = useState("");
  const [view, setView] = useState<"scan" | "audit">("scan");
  const [isScanning, setIsScanning] = useState(false);

  const handleVerify = async (payload: string) => {
    setError("");
    setResult(null);

    try {
      const response = await api.post("/api/v1/access/verify", {
        qr_payload: payload,
      });
      setResult(response.data);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Verification failed";
      // Try to extract detail from Axios error
      if (err && typeof err === "object" && "response" in err) {
        const axiosErr = err as { response?: { data?: { detail?: string } } };
        setError(axiosErr.response?.data?.detail || msg);
      } else {
        setError(msg);
      }
    }
  };

  const handleManualVerify = () => {
    if (!qrInput.trim()) return;
    handleVerify(qrInput.trim());
  };

  const handleScanned = (payload: string) => {
    setQrInput(payload);
    setIsScanning(false);
    handleVerify(payload);
  };

  return (
    <div style={{ maxWidth: 700, margin: "2rem auto", padding: "0 1rem" }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: "1rem",
        }}
      >
        <h1 style={{ margin: 0 }}>Checker Dashboard</h1>
        <button onClick={onLogout} style={{ padding: "0.5rem 1rem" }}>
          Logout
        </button>
      </div>

      <p>
        Role: <strong>{role}</strong>
      </p>

      {/* Tab navigation */}
      <div style={{ display: "flex", gap: 0, marginBottom: "1.5rem" }}>
        <button
          onClick={() => setView("scan")}
          style={{
            padding: "0.5rem 1.25rem",
            border: view === "scan" ? "2px solid #2563eb" : "2px solid #ccc",
            background: view === "scan" ? "#eff6ff" : "white",
            borderRight: 0,
            borderRadius: "4px 0 0 4px",
            cursor: "pointer",
            fontWeight: view === "scan" ? 600 : 400,
          }}
        >
          QR Scanner
        </button>
        {role === "manager" && (
          <button
            onClick={() => setView("audit")}
            style={{
              padding: "0.5rem 1.25rem",
              border: view === "audit" ? "2px solid #2563eb" : "2px solid #ccc",
              background: view === "audit" ? "#eff6ff" : "white",
              borderRadius: "0 4px 4px 0",
              cursor: "pointer",
              fontWeight: view === "audit" ? 600 : 400,
            }}
          >
            Audit Logs
          </button>
        )}
      </div>

      {view === "scan" && (
        <>
          {/* Camera scanner toggle */}
          <div style={{ marginBottom: "1rem" }}>
            <button
              onClick={() => setIsScanning(!isScanning)}
              style={{
                width: "100%",
                padding: "0.6rem",
                fontSize: "1rem",
                cursor: "pointer",
                background: isScanning ? "#dc2626" : "#2563eb",
                color: "white",
                border: "none",
                borderRadius: 4,
              }}
            >
              {isScanning ? "Stop Camera" : "Start Camera Scanner"}
            </button>
          </div>

          {isScanning && <QRScanner onScan={handleScanned} isScanning={isScanning} />}

          {/* Manual paste input */}
          <div style={{ marginBottom: "1rem" }}>
            <label
              htmlFor="qr-input"
              style={{ display: "block", marginBottom: "0.5rem", fontWeight: 500 }}
            >
              Manual QR Payload (paste)
            </label>
            <textarea
              id="qr-input"
              value={qrInput}
              onChange={(e) => setQrInput(e.target.value)}
              rows={3}
              style={{ width: "100%", padding: "0.5rem", fontSize: "0.875rem", boxSizing: "border-box" }}
              placeholder="V1|resident-id|timestamp|signature"
            />
          </div>

          <button
            onClick={handleManualVerify}
            disabled={!qrInput.trim()}
            style={{
              width: "100%",
              padding: "0.75rem",
              fontSize: "1rem",
              cursor: qrInput.trim() ? "pointer" : "not-allowed",
              opacity: qrInput.trim() ? 1 : 0.5,
              background: "#059669",
              color: "white",
              border: "none",
              borderRadius: 4,
            }}
          >
            Verify QR Code
          </button>

          {error && <div style={{ color: "#dc2626", marginTop: "1rem" }}>{error}</div>}

          {result && (
            <div
              style={{
                marginTop: "1rem",
                padding: "1rem",
                borderRadius: 4,
                background:
                  result.status === "valid"
                    ? "#d4edda"
                    : result.status === "expired"
                      ? "#fff3cd"
                      : "#f8d7da",
              }}
            >
              <p style={{ fontSize: "1.5rem", fontWeight: "bold", margin: 0 }}>
                {result.status === "valid"
                  ? "✓ Valid"
                  : result.status === "expired"
                    ? "⏱ Expired"
                    : "✗ Invalid"}
              </p>
              {isManagerResponse(result) && result.status === "valid" && (
                <>
                  <p>Resident: {result.resident_name}</p>
                  <p>Unit: {result.unit}</p>
                </>
              )}
            </div>
          )}
        </>
      )}

      {view === "audit" && role === "manager" && <AuditLogViewer />}
    </div>
  );
}