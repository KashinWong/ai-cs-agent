import { defineConfig } from "vite";

export default defineConfig({
  base: "/widget/",
  build: { outDir: "dist", emptyOutDir: true },
  server: {
    proxy: {
      "/api": "http://localhost:8000",
      "/ws": { target: "ws://localhost:8000", ws: true },
    },
  },
});
