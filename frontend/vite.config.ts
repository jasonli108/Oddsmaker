import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // In dev the browser calls /api on this origin and Vite forwards it to FastAPI.
    proxy: { '/api': 'http://localhost:8000' },
  },
});
