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
  void clearRecording();
}

// A recording (mic or upload) is kept the same way, but in IndexedDB on this device, since a recording is too big for
// sessionStorage. It is only there so a family whose film failed can press "Make my wayang" again without telling the
// story again. It is removed as soon as a film is done, and ignored (and removed) after RECORDING_TTL_MS.
const DB = "dalang";
const STORE = "draft";
const REC_KEY = "recording";
export const RECORDING_TTL_MS = 6 * 60 * 60 * 1000;

export interface SavedRecording {
  blob: Blob;
  name: string;
  lang: "id" | "jv" | "en";
  saved: number;
}

function openDb(): Promise<IDBDatabase | null> {
  return new Promise((resolve) => {
    try {
      if (typeof indexedDB === "undefined") return resolve(null);
      const req = indexedDB.open(DB, 1);
      req.onupgradeneeded = () => req.result.createObjectStore(STORE);
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => resolve(null);
    } catch {
      resolve(null);
    }
  });
}

async function withStore<T>(mode: IDBTransactionMode, fn: (s: IDBObjectStore) => IDBRequest<T>): Promise<T | null> {
  const db = await openDb();
  if (!db) return null;
  return new Promise((resolve) => {
    try {
      const req = fn(db.transaction(STORE, mode).objectStore(STORE));
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => resolve(null);
    } catch {
      resolve(null);
    }
  }).finally(() => db.close()) as Promise<T | null>;
}

export async function saveRecording(r: Omit<SavedRecording, "saved">): Promise<void> {
  await withStore("readwrite", (s) => s.put({ ...r, saved: Date.now() }, REC_KEY));
}

export async function readRecording(now: number = Date.now()): Promise<SavedRecording | null> {
  const r = (await withStore("readonly", (s) => s.get(REC_KEY))) as SavedRecording | null | undefined;
  if (!r || !(r.blob instanceof Blob) || !["id", "jv", "en"].includes(r.lang)) return null;
  if (now - r.saved > RECORDING_TTL_MS) {
    await clearRecording();
    return null;
  }
  return r;
}

export async function clearRecording(): Promise<void> {
  await withStore("readwrite", (s) => s.delete(REC_KEY));
}
