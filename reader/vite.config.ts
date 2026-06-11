import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { VitePWA } from "vite-plugin-pwa";

// swenia reader — installable PWA. Reads /latest.json (synced from the
// pipeline's output/ in dev; served from the same origin in prod).
export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: "autoUpdate",
      includeAssets: ["favicon.svg"],
      manifest: {
        name: "swenia",
        short_name: "swenia",
        description: "Your daily AI/tech frontier digest.",
        theme_color: "#0a0a0a",
        background_color: "#fafafa",
        display: "standalone",
        icons: [
          { src: "icon-192.png", sizes: "192x192", type: "image/png" },
          { src: "icon-512.png", sizes: "512x512", type: "image/png" },
          {
            src: "icon-512.png",
            sizes: "512x512",
            type: "image/png",
            purpose: "maskable",
          },
        ],
      },
      workbox: {
        // Always try network first for the digest so a fresh day shows up;
        // fall back to cache offline.
        runtimeCaching: [
          {
            urlPattern: /\/latest\.json$/,
            handler: "NetworkFirst",
            options: { cacheName: "digest" },
          },
        ],
      },
    }),
  ],
});
