import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

const backendHost = process.env.BACKEND_HOST ?? "localhost";
const backendPort = process.env.BACKEND_PORT ?? "8000";
const backendOrigin = `${backendHost}:${backendPort}`;

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    host: true,
    port: 5173,
    proxy: {
      "/api": {
        target: `http://${backendOrigin}`,
        changeOrigin: true,
      },
      "/ws": {
        target: `ws://${backendOrigin}`,
        ws: true,
      },
    },
  },
});