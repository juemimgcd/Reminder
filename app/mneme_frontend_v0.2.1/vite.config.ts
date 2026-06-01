import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import path from 'path';
import {defineConfig} from 'vite';

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, '.'),
    },
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (!id.includes("node_modules")) {
            return;
          }
          if (id.includes("d3")) {
            return "graph-vendor";
          }
          if (id.includes("react-markdown")) {
            return "markdown-vendor";
          }
          if (id.includes("lucide-react")) {
            return "ui-vendor";
          }
          if (id.includes("react") || id.includes("scheduler")) {
            return "react-vendor";
          }
          return "vendor";
        },
      },
    },
  },
  server: {
    host: '0.0.0.0',
    port: 3000,
  },
});
