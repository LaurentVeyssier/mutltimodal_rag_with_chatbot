import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://127.0.0.1:8000/:path*',
      },
    ];
  },
  experimental: {
    serverActions: {
      allowedOrigins: ['localhost:3000', '*.lhr.life', '*.trycloudflare.com', '*.ngrok-free.app'],
    },
  },
};

export default nextConfig;
