/**
 * All /api and /media requests are proxied to the Python backend, so the phone only needs one URL.
 * API_ORIGIN is read at BUILD time (Next.js bakes rewrites into the build). On Vercel, set it under
 * Project Settings -> Environment Variables (e.g. https://dalang-ai-api.onrender.com) and redeploy.
 */
const API = process.env.API_ORIGIN || "http://127.0.0.1:8000";

// Same origin for everything except film files, which may come from the R2 bucket (STORAGE_R2_PUBLIC_URL) over https.
// Inline scripts stay allowed: Next.js boots with inline scripts and the day/night switch runs one before paint.
const CSP = [
  "default-src 'self'",
  "script-src 'self' 'unsafe-inline'",
  "style-src 'self' 'unsafe-inline'",
  "img-src 'self' data: blob: https:",
  "media-src 'self' blob: https:",
  "font-src 'self' data:",
  "connect-src 'self'",
  "worker-src 'self'",
  "manifest-src 'self'",
  "frame-ancestors 'self'",
  "base-uri 'self'",
  "form-action 'self'",
  "object-src 'none'",
].join("; ");

const SECURITY_HEADERS = [
  { key: "Content-Security-Policy", value: CSP },
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  { key: "X-Frame-Options", value: "SAMEORIGIN" },
  // the story recorder is the only thing that needs a device
  { key: "Permissions-Policy", value: "microphone=(self), camera=(), geolocation=(), payment=()" },
];

const nextConfig = {
  poweredByHeader: false,
  async headers() {
    // next dev needs eval for fast refresh, so the policy only goes on production builds
    if (process.env.NODE_ENV !== "production") return [];
    // every path except /api/docs (the API's Swagger page, proxied; it loads its script from a CDN and runs inline)
    return [
      { source: "/((?!api/docs$).*)", headers: SECURITY_HEADERS },
      { source: "/api/docs", headers: SECURITY_HEADERS.filter((h) => h.key !== "Content-Security-Policy") },
    ];
  },
  // NEXT_DIST_DIR lets a second build (another API_ORIGIN, e.g. a screenshot server) sit next to the default .next
  distDir: process.env.NEXT_DIST_DIR || ".next",
  compress: false, // keeps Server-Sent Events streaming through the proxy
  async rewrites() {
    return [
      { source: "/api/:path*", destination: `${API}/api/:path*` },
      { source: "/media/:path*", destination: `${API}/media/:path*` },
    ];
  },
};
export default nextConfig;
