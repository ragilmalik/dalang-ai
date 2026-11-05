// A typed story is kept in this tab (sessionStorage) from "Make my wayang" until its film is done, so a family whose
// film failed, or was stopped by Penjaga Budaya, finds the story still in the box when they go back to try again.
const KEY = "dalang:draft";

export interface Draft {
  text: string;
  lang: "id" | "jv" | "en";
}

export function saveDraft(d: Draft): void {
  try {
    sessionStorage.setItem(KEY, JSON.stringify(d));
  } catch {
    /* private mode or storage full: nothing to keep */
  }
}

export function readDraft(): Draft | null {
  try {
    const d = JSON.parse(sessionStorage.getItem(KEY) || "null") as Draft | null;
    return d && typeof d.text === "string" && d.text.trim() && ["id", "jv", "en"].includes(d.lang) ? d : null;
  } catch {
    return null;
  }
}

export function clearDraft(): void {
  try {
    sessionStorage.removeItem(KEY);
  } catch {
    /* nothing kept */
  }
}
