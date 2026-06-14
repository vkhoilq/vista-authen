import { useState } from "react";
import LoginScreen from "./screens/LoginScreen";
import Dashboard from "./screens/Dashboard";

function App() {
  const [token, setToken] = useState(() => sessionStorage.getItem("token") || "");
  const [role, setRole] = useState<"guard" | "manager" | null>(() => {
    return sessionStorage.getItem("role") as "guard" | "manager" | null;
  });

  const handleLogin = (jwt: string, userRole: "guard" | "manager") => {
    sessionStorage.setItem("token", jwt);
    sessionStorage.setItem("role", userRole);
    setToken(jwt);
    setRole(userRole);
  };

  const handleLogout = () => {
    sessionStorage.removeItem("token");
    sessionStorage.removeItem("role");
    setToken("");
    setRole(null);
  };

  if (!token || !role) {
    return <LoginScreen onLogin={handleLogin} />;
  }

  return <Dashboard role={role} token={token} onLogout={handleLogout} />;
}

export default App;
