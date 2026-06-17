import { useState } from "react";
import axios from "axios";
import { api } from "@vista-authen/shared";

interface LoginScreenProps {
  onLogin: (jwt: string, role: string) => void;
}

export default function LoginScreen({ onLogin }: LoginScreenProps) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const response = await api.post("/api/v1/auth/admin/login", {
        username,
        password,
      });
      onLogin(response.data.access_token, response.data.role);
    } catch (err: unknown) {
      if (axios.isAxiosError(err) && err.response?.data?.detail) {
        setError(err.response.data.detail);
      } else if (axios.isAxiosError(err) && err.message) {
        setError(`Network error: ${err.message}`);
      } else {
        setError(err instanceof Error ? err.message : "Login failed");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ maxWidth: 400, margin: "6rem auto", padding: "2rem", background: "white", borderRadius: 8, boxShadow: "0 4px 6px -1px rgba(0, 0, 0, 0.1)" }}>
      <h2 style={{ textAlign: "center", marginBottom: "1.5rem", color: "#1f2937" }}>Admin Portal Login</h2>
      <form onSubmit={handleLogin}>
        <div style={{ marginBottom: "1rem" }}>
          <label htmlFor="username" style={{ display: "block", marginBottom: "0.5rem", color: "#4b5563", fontWeight: 500 }}>
            Username
          </label>
          <input
            id="username"
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            style={{ width: "100%", padding: "0.5rem", fontSize: "1rem", borderRadius: 4, border: "1px solid #d1d5db", boxSizing: "border-box" }}
            placeholder="Enter admin username"
          />
        </div>

        <div style={{ marginBottom: "1.5rem" }}>
          <label htmlFor="password" style={{ display: "block", marginBottom: "0.5rem", color: "#4b5563", fontWeight: 500 }}>
            Password
          </label>
          <input
            id="password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            style={{ width: "100%", padding: "0.5rem", fontSize: "1rem", borderRadius: 4, border: "1px solid #d1d5db", boxSizing: "border-box" }}
            placeholder="Enter password"
          />
        </div>

        {error && <div style={{ color: "#dc2626", marginBottom: "1rem", fontSize: "0.875rem", textAlign: "center" }}>{error}</div>}

        <button
          type="submit"
          disabled={!username || !password || loading}
          style={{
            width: "100%",
            padding: "0.75rem",
            fontSize: "1rem",
            color: "white",
            backgroundColor: "#2563eb",
            border: "none",
            borderRadius: 4,
            fontWeight: 600,
            cursor: username && password && !loading ? "pointer" : "not-allowed",
            opacity: username && password && !loading ? 1 : 0.7,
            transition: "background-color 0.2s",
          }}
        >
          {loading ? "Logging in..." : "Login"}
        </button>
      </form>
    </div>
  );
}
