import { useState, useEffect, useCallback } from "react";
import { QRCodeSVG } from "qrcode.react";
import { signPayload, buildQrPayload, getCurrentTimestamp, getSecondsUntilRotation } from "@vista-authen/shared";

export default function QRScreen() {
  const residentId = localStorage.getItem("resident_id")!;
  const [qrPayload, setQrPayload] = useState("");
  const [countdown, setCountdown] = useState(30);

  const generateQr = useCallback(async () => {
    const privateKeyJwk = JSON.parse(localStorage.getItem("private_key")!);
    const privateKey = await crypto.subtle.importKey(
      "jwk",
      privateKeyJwk,
      { name: "ECDSA", namedCurve: "P-256" },
      true,
      ["sign"],
    );

    const timestamp = getCurrentTimestamp();
    const payload = `${residentId}|${timestamp}`;
    const signatureB64 = await signPayload(payload, privateKey);
    const qrString = buildQrPayload(residentId, timestamp, signatureB64);

    setQrPayload(qrString);
    setCountdown(getSecondsUntilRotation());
  }, [residentId]);

  useEffect(() => {
    let lastSlot = Math.floor(Date.now() / 30000);
    generateQr();

    const timer = setInterval(() => {
      const now = Date.now();
      const slot = Math.floor(now / 30000);
      setCountdown(30 - (Math.floor(now / 1000) % 30));

      if (slot !== lastSlot) {
        lastSlot = slot;
        generateQr();
      }
    }, 1000);

    return () => clearInterval(timer);
  }, [generateQr]);

  return (
    <div style={{ maxWidth: 400, margin: "2rem auto", padding: "0 1rem", textAlign: "center" }}>
      <h1>Access QR Code</h1>
      <p>Resident: {residentId}</p>

      {qrPayload && (
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "1rem" }}>
          <div style={{ padding: "1rem", background: "white", display: "inline-block" }}>
            <QRCodeSVG value={qrPayload} size={256} />
          </div>
          <div style={{ width: "100%", maxWidth: 300 }}>
            <textarea
              readOnly
              value={qrPayload}
              style={{
                width: "100%",
                height: "60px",
                fontFamily: "monospace",
                fontSize: "0.75rem",
                padding: "0.5rem",
                borderRadius: "4px",
                border: "1px solid #ccc",
                resize: "none",
              }}
            />
            <button
              onClick={() => navigator.clipboard.writeText(qrPayload)}
              style={{
                marginTop: "0.5rem",
                width: "100%",
                padding: "0.5rem",
                fontSize: "0.9rem",
                cursor: "pointer",
                backgroundColor: "#007bff",
                color: "white",
                border: "none",
                borderRadius: "4px",
              }}
            >
              Copy Raw QR Payload
            </button>
          </div>
        </div>
      )}

      <p style={{ fontSize: "1.5rem", fontWeight: "bold", marginTop: "1rem" }}>
        Refreshes in: {countdown}s
      </p>

      <div
        style={{
          marginTop: "1rem",
          padding: "0.75rem",
          background: "#fff3cd",
          borderRadius: "4px",
          fontSize: "0.875rem",
        }}
      >
        ⚠️ Web client — QR codes are not hardware-bound. Production uses mobile Secure Enclave.
      </div>
    </div>
  );
}
