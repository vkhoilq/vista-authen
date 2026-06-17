import { useState } from "react";
import LoginScreen from "./screens/LoginScreen";
import Dashboard from "./screens/Dashboard";

function App() {
  const [token, setToken] = useState(() => sessionStorage.getItem("token") || "");
  const [role, setRole] = useState<string | null>(() => {
    return sessionStorage.getItem("role");
  });

  const handleLogin = (jwt: string, adminRole: string) => {
    sessionStorage.setItem("token", jwt);
    sessionStorage.setItem("role", adminRole);
    setToken(jwt);
    setRole(adminRole);
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
