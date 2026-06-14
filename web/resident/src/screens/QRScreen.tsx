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
    const payload = `V1|${residentId}|${timestamp}`;
    const signatureB64 = await signPayload(payload, privateKey);
    const qrString = buildQrPayload(residentId, timestamp, signatureB64);

    setQrPayload(qrString);
    setCountdown(getSecondsUntilRotation());
  }, [residentId]);

  useEffect(() => {
    generateQr();

    const interval = setInterval(() => {
      generateQr();
    }, 30000);

    const countdownInterval = setInterval(() => {
      setCountdown((prev) => Math.max(0, prev - 1));
    }, 1000);

    return () => {
      clearInterval(interval);
      clearInterval(countdownInterval);
    };
  }, [generateQr]);

  return (
    <div style={{ maxWidth: 400, margin: "2rem auto", padding: "0 1rem", textAlign: "center" }}>
      <h1>Access QR Code</h1>
      <p>Resident: {residentId}</p>

      {qrPayload && (
        <div style={{ display: "inline-block", padding: "1rem", background: "white" }}>
          <QRCodeSVG value={qrPayload} size={256} />
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
