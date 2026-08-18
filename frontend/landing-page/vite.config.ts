import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Standalone dev: Vite on 5173, Jahia-adapter backend on 8799. /api proxied to the backend so the
// browser never sees the Jahia token.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: { "/api": "http://localhost:8799" },
  },
});
