import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Trigger GitHub Pages deployment
export default defineConfig({
  plugins: [react()],
  base: "/VISIONPROMPT-AI/",
});