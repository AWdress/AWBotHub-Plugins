import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import federation from '@originjs/vite-plugin-federation'

export default defineConfig({
  base: '/api/plugins/ssd_assistant/fe/',
  plugins: [vue(), federation({
    name: 'awbothub_ssd_assistant',
    filename: 'remoteEntry.js',
    exposes: { './Config': './src/Config.vue' },
    shared: { vue: { singleton: true, requiredVersion: false, generate: false } },
    format: 'esm',
  })],
  build: { target: 'esnext', minify: false, cssCodeSplit: true },
  server: { host: '127.0.0.1', port: 5021, cors: true },
})
