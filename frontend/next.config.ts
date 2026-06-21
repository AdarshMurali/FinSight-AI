import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Allow fetching from local FastAPI backend
  async headers() {
    return [
      {
        source: "/(.*)",
        headers: [{ key: "X-Content-Type-Options", value: "nosniff" }],
      },
    ];
  },
};

export default nextConfig;
