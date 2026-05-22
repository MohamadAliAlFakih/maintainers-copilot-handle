// Vite config: bundles to a single chunk for cache-friendly embedding.
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  build: {
    target: "es2020",
    rollupOptions: {
      output: {
        manualChunks: undefined,
        entryFileNames: "assets/widget-[hash].js",
        chunkFileNames: "assets/widget-[hash].js",
        assetFileNames: "assets/widget-[hash][extname]",
      },
    },
    cssCodeSplit: false,
    sourcemap: false,
  },
});
