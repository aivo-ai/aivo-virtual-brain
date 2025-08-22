import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    react(),
    // Temporarily completely disable PWA to clear all caches
    // VitePWA({
    //   registerType: 'autoUpdate',
    //   srcDir: 'src',
    //   filename: 'sw.ts',
    //   strategies: 'injectManifest',
    //   injectManifest: {
    //     globPatterns: ['**/*.{js,css,html,ico,png,svg,woff,woff2}'],
    //     maximumFileSizeToCacheInBytes: 5 * 1024 * 1024, // 5MB
    //   },
    //   workbox: {
    //     globPatterns: ['**/*.{js,css,html,ico,png,svg,woff,woff2}'],
    //     maximumFileSizeToCacheInBytes: 5 * 1024 * 1024, // 5MB
    //     runtimeCaching: [
    //       {
    //         urlPattern: /^https:\/\/api\.aivo\.*/,
    //         handler: 'StaleWhileRevalidate',
    //         options: {
    //           cacheName: 'api-cache',
    //           expiration: {
    //             maxEntries: 50,
    //             maxAgeSeconds: 10 * 60, // 10 minutes
    //           },
    //         },
    //       },
    //       {
    //         urlPattern: /\.(?:png|jpg|jpeg|svg|gif|webp)$/,
    //         handler: 'CacheFirst',
    //         options: {
    //           cacheName: 'images',
    //           expiration: {
    //             maxEntries: 100,
    //             maxAgeSeconds: 7 * 24 * 60 * 60, // 7 days
    //           },
    //         },
    //       },
    //     ],
    //   },
    //   devOptions: {
    //     enabled: false, // Disabled in development to prevent caching issues
    //     type: 'module',
    //   },
    //   manifest: {
    //     name: 'Aivo Virtual Brains',
    //     short_name: 'Aivo',
    //     description: 'AI-powered personalized learning platform',
    //     theme_color: '#000000',
    //     background_color: '#ffffff',
    //     display: 'standalone',
    //     orientation: 'portrait-primary',
    //     scope: '/',
    //     start_url: '/',
    //     icons: [
    //       {
    //         src: '/pwa-64x64.png',
    //         sizes: '64x64',
    //         type: 'image/png',
    //       },
    //       {
    //         src: '/pwa-192x192.png',
    //         sizes: '192x192',
    //         type: 'image/png',
    //       },
    //       {
    //         src: '/pwa-512x512.png',
    //         sizes: '512x512',
    //         type: 'image/png',
    //         purpose: 'any',
    //       },
    //       {
    //         src: '/maskable-icon-512x512.png',
    //         sizes: '512x512',
    //         type: 'image/png',
    //         purpose: 'maskable',
    //       },
    //     ],
    //     categories: ['education', 'productivity'],
    //     screenshots: [
    //       {
    //         src: '/screenshot-wide.png',
    //         sizes: '1280x720',
    //         type: 'image/png',
    //         form_factor: 'wide',
    //       },
    //       {
    //         src: '/screenshot-mobile.png',
    //         sizes: '720x1280',
    //         type: 'image/png',
    //         form_factor: 'narrow',
    //       },
    //     ],
    //   },
    // }),
  ],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 3000,
    host: true,
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom'],
          router: ['react-router-dom'],
          ui: ['framer-motion', '@heroicons/react'],
        },
      },
    },
  },
})
