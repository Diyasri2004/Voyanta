import type { NextConfig } from "next";

const BACKEND_URL = (process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000").trim().replace(/\/$/, "");
// Local dev only: Vercel already forwards /api/* to the backend via vercel.json
const useDevProxy = !process.env.VERCEL && /^https?:\/\//.test(BACKEND_URL);

const nextConfig: NextConfig = {
  // Proxy API calls the frontend has no route for to the FastAPI backend
  async rewrites() {
    return {
      beforeFiles: [],
      afterFiles: [],
      fallback: useDevProxy ? [{ source: "/api/:path*", destination: `${BACKEND_URL}/api/:path*` }] : [],
    };
  },
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "images.pexels.com",
        pathname: "/**",
      },
    ],
  },
};

export default nextConfig;
