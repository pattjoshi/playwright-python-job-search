import type { NextConfig } from "next";

// `npm run build` exports plain static files to out/, which the Python backend serves on
// http://127.0.0.1:8000. During `npm run dev` the page runs on :3000 and API calls are
// forwarded to the backend, so start it too (python -m job_search serve --no-open).
const isDev = process.env.NODE_ENV === "development";
const backendUrl = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  ...(isDev
    ? {
        async rewrites() {
          return [
            { source: "/api/:path*", destination: `${backendUrl}/api/:path*` },
            { source: "/reports/:path*", destination: `${backendUrl}/reports/:path*` },
          ];
        },
      }
    : { output: "export" }),
  images: { unoptimized: true }, // static export: images are served as they are
  reactStrictMode: true,
  poweredByHeader: false,
};

export default nextConfig;
