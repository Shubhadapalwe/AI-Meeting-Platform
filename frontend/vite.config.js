import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import fs from "fs";

export default defineConfig(() => {
  const certFile = "/certs/cert.pem";
  const keyFile  = "/certs/key.pem";
  const hasHttps = fs.existsSync(certFile) && fs.existsSync(keyFile);

  return {
    plugins: [react()],
    server: {
      host: "0.0.0.0",
      port: 5173,
      // Enable HTTPS when certs are mounted into the container
      ...(hasHttps
        ? { https: { cert: fs.readFileSync(certFile), key: fs.readFileSync(keyFile) } }
        : {}),
      proxy: {
        // All API calls → backend (HTTP server-side, no mixed-content issue)
        "/api": {
          target: "http://backend:8000",
          changeOrigin: true,
        },
        // LiveKit WebSocket proxied through Vite so browser uses wss:// (same origin)
        // Browser: wss://HOST_IP:5173/livekit  →  ws://livekit:7880
        "/livekit": {
          target: "ws://livekit:7880",
          ws: true,
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/livekit/, "") || "/",
        },
      },
    },
  };
});
