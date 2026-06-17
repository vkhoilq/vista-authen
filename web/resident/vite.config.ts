import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const allowedHosts = env.VITE_ALLOWED_HOSTS
    ? env.VITE_ALLOWED_HOSTS.split(",")
    : ["localhost", "127.0.0.1", "192.168.100.223"];

  return {
    plugins: [react()],
    server: {
      port: 62146,
      allowedHosts: allowedHosts,
    },
  };
});
