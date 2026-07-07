import tailwindcss from '@tailwindcss/vite';
import vue from '@vitejs/plugin-vue';
import path from 'path';
import { fileURLToPath } from 'url';
import {defineConfig} from 'vite';

const dirname = path.dirname(fileURLToPath(import.meta.url));

export default defineConfig({
  plugins: [vue(), tailwindcss()],
  resolve: {
    alias: {
      '@': path.resolve(dirname, '.'),
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
          if (id.includes("@lucide/vue")) {
            return "ui-vendor";
          }
          if (id.includes("vue")) {
            return "vue-vendor";
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
