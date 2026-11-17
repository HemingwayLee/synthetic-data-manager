import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The path nginx serves this app under. Pages, assets and the HMR websocket all live below it, so one nginx
// location (/randomHtmlTables/) covers the whole frontend. Must start and end with "/".
const base = process.env.BASE_PATH || "/randomHtmlTables/";
const apiTarget = process.env.API_PROXY_TARGET || "http://localhost:8102";

export default defineConfig({
  base,
  plugins: [react()],
  server: {
    host: true,
    port: Number(process.env.PORT) || 5102,
    strictPort: true,
    // Behind nginx the Host header is the public hostname, not localhost. Dev server only.
    allowedHosts: true,
    // Polling makes file watching reliable across Docker bind mounts.
    watch: { usePolling: process.env.VITE_USE_POLLING === "true" },
    // When opened directly (http://localhost:5102/randomHtmlTables/) rather than through nginx, proxy the API the same way
    // nginx does: /randomHtmlTables/api/* -> backend /api/*.
    proxy: {
      [`${base}api`]: { target: apiTarget, rewrite: (path) => path.slice(base.length - 1) },
    },
  },
});
