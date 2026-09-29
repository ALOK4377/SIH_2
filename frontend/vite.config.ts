import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Dev server runs on 5173; the backend origin is read from VITE_API_BASE
// (see .env.example). `host: true` lets it work inside Docker.
export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 5173,
  },
});
