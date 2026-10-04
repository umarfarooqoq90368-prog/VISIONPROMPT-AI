import {defineConfig} from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  base: "/VISIONPROMPT-AI/",
  server: {
    port: 1492,
  },
  build: {
    outDir: "dist",
  },
});