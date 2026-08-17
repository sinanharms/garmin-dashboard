import react from "@vitejs/plugin-react-swc";
import { defineConfig } from "vite";

export default defineConfig({
  base: "/static/app/",
  plugins: [react()],
  build: {
    outDir: "dist",
  },
  server: {
    proxy: { "/api": "http://127.0.0.1:8000" },
  },
});
