import type { MetadataRoute } from "next";

// "Add to Home Screen" on phones: the app opens full screen with the gunungan icon.
export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "Dalang AI · Ceritamu jadi wayang",
    short_name: "Dalang AI",
    description: "A child tells a story out loud. Six Meta models perform it as a Javanese shadow-puppet film.",
    start_url: "/",
    display: "standalone",
    background_color: "#0C0A1E",
    theme_color: "#0C0A1E",
    lang: "id",
    shortcuts: [
      { name: "Pentas · Showcase", short_name: "Pentas", url: "/pentas" },
      { name: "Ceritakan · Tell a story", short_name: "Cerita", url: "/#cerita" },
    ],
    icons: [
      { src: "/icon-192.png", sizes: "192x192", type: "image/png" },
      { src: "/icon-512.png", sizes: "512x512", type: "image/png" },
      { src: "/icon-maskable-512.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
    ],
  };
}
