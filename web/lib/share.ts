// One place for the words a shared film carries, so the film page, the watch page and the tests agree.
export const SHARE_HASHTAGS = ["DalangCilik", "wayang", "MetaHackathon"]; // #DalangCilik = the launch challenge (docs/X_LAUNCH.md)

/** Short default post: fits X with the link and leaves room for the parent's own words. */
export function shareText(title: string): string {
  const t = title.trim() || "my story";
  return `My story became a wayang kulit film: "${t}" 🎭 Made with Dalang AI on Meta Muse models.`;
}

/** X (Twitter) web intent; hashtags go in their own parameter so X links them. */
export function xIntent(title: string, url: string): string {
  const q = new URLSearchParams({ text: shareText(title), url, hashtags: SHARE_HASHTAGS.join(",") });
  return `https://x.com/intent/post?${q.toString()}`;
}

/** File name for a downloaded film: the title in plain letters, plus the shape. */
export function filmFileName(title: string, shape: "landscape" | "vertical"): string {
  const base = (title || "dalang").normalize("NFKD").replace(/[^\w\s-]/g, "").trim().replace(/\s+/g, "-").slice(0, 60);
  return `${base || "dalang"}${shape === "vertical" ? "-9x16" : "-16x9"}.mp4`;
}
