import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import path from "path";

// Inside Docker Compose, the frontend container must reach the backend
// by its service name ("backend"), not "localhost" — each container has
// its own localhost. BACKEND_HOST lets docker-compose.yml override this;
// it defaults to localhost for running `npm run dev` directly on your host.
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
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    include: ["src/**/*.test.{ts,tsx}"],
    css: false,
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
