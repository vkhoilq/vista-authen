import { useState } from "react";
import { api, generateKeyPair } from "@vista-authen/shared";

import axios from "axios";

interface ActivationScreenProps {
  onActivated: () => void;
}

export default function ActivationScreen({ onActivated }: ActivationScreenProps) {
  const [token, setToken] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleActivate = async () => {
    setError("");
    setLoading(true);

    try {
      const { publicKeyPem, privateKey } = await generateKeyPair();

      // Store private key in localStorage (TESTING ONLY — mobile uses Secure Enclave)
      const privateKeyJwk = await crypto.subtle.exportKey("jwk", privateKey);
      localStorage.setItem("private_key", JSON.stringify(privateKeyJwk));

      const response = await api.post("/api/v1/residents/register", {
        activation_token: token,
        public_key_pem: publicKeyPem,
      });

      localStorage.setItem("resident_id", response.data.id);
      onActivated();
    } catch (err: unknown) {
      if (axios.isAxiosError(err) && err.response?.data?.detail) {
        setError(err.response.data.detail);
      } else if (axios.isAxiosError(err) && err.message) {
        setError(`Network error: ${err.message}`);
      } else {
        setError(err instanceof Error ? err.message : "Activation failed");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ maxWidth: 400, margin: "2rem auto", padding: "0 1rem" }}>
      <h1>Resident Activation</h1>
      <p>Enter the one-time activation token provided by building management.</p>

      <div style={{ marginBottom: "1rem" }}>
        <label htmlFor="token" style={{ display: "block", marginBottom: "0.5rem" }}>
          Activation Token
        </label>
        <input
          id="token"
          type="text"
          value={token}
          onChange={(e) => setToken(e.target.value)}
          placeholder="Enter activation token"
          style={{ width: "100%", padding: "0.5rem", fontSize: "1rem" }}
        />
      </div>

      {error && <div style={{ color: "red", marginBottom: "1rem" }}>{error}</div>}

      <button
        onClick={handleActivate}
        disabled={!token || loading}
        style={{
          width: "100%",
          padding: "0.75rem",
          fontSize: "1rem",
          cursor: token && !loading ? "pointer" : "not-allowed",
          opacity: token && !loading ? 1 : 0.5,
        }}
      >
        {loading ? "Activating..." : "Activate Device"}
      </button>

      <div
        style={{
          marginTop: "2rem",
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
