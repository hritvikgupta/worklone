import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import path from 'path';
import {defineConfig, loadEnv} from 'vite';

export default defineConfig(({mode}) => {
  const env = loadEnv(mode, '.', '');
  const allowedHosts = new Set<string>(['localhost', '127.0.0.1']);

  // Support dynamic tunnel domains without editing code every time.
  if (env.VITE_ALLOWED_HOSTS) {
    for (const host of env.VITE_ALLOWED_HOSTS.split(',')) {
      const normalized = host.trim();
      if (normalized) allowedHosts.add(normalized);
    }
  }

  // Temporary explicit host currently used in local testing.
  allowedHosts.add('consistency-flex-integrating-itunes.trycloudflare.com');

  return {
    plugins: [react(), tailwindcss()],
    define: {
      'process.env.GEMINI_API_KEY': JSON.stringify(env.GEMINI_API_KEY),
    },
    resolve: {
      alias: {
        '@': path.resolve(__dirname, '.'),
      },
    },
    server: {
      // HMR is disabled in AI Studio via DISABLE_HMR env var.
      // Do not modifyâfile watching is disabled to prevent flickering during agent edits.
      hmr: process.env.DISABLE_HMR !== 'true',
      allowedHosts: [...allowedHosts],
    },
  };
});
