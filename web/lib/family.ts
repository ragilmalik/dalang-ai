// Kotak Wayang (puppet box) helpers. No accounts: a random family id lives only in this browser's localStorage.

export interface KotakPuppet {
  id: string;
  char_id: string;
  name: string;
  kind: string;
  archetype: string;
  look: string;
  note: string;
  cutout: string;
  created: number;
  source_job: string;
}

const FAMILY_KEY = "dalang_family";
const RETURNING_KEY = "dalang_returning";

export function familyId(): string {
  if (typeof window === "undefined") return "";
  let id = localStorage.getItem(FAMILY_KEY);
  if (!id || !/^[A-Za-z0-9_-]{16,64}$/.test(id)) {
    const bytes = new Uint8Array(16);
    crypto.getRandomValues(bytes);
    id = "fam_" + Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
    localStorage.setItem(FAMILY_KEY, id);
  }
  return id;
}

export function getReturning(): string[] {
  if (typeof window === "undefined") return [];
  try {
    const v = JSON.parse(localStorage.getItem(RETURNING_KEY) || "[]");
    return Array.isArray(v) ? v.filter((x) => typeof x === "string").slice(0, 3) : [];
  } catch {
    return [];
  }
}

export function setReturning(ids: string[]): void {
  localStorage.setItem(RETURNING_KEY, JSON.stringify(ids.slice(0, 3)));
}

export async function listKotak(): Promise<KotakPuppet[]> {
  const r = await fetch(`/api/kotak?family=${encodeURIComponent(familyId())}`);
  return r.ok ? ((await r.json()) as KotakPuppet[]) : [];
}

export async function savePuppet(jobId: string, charId: string): Promise<KotakPuppet> {
  const r = await fetch("/api/kotak", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ family_id: familyId(), job_id: jobId, char_id: charId }),
  });
  if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail || r.statusText);
  return (await r.json()) as KotakPuppet;
}

export async function deletePuppet(id: string): Promise<void> {
  await fetch(`/api/kotak/${id}?family=${encodeURIComponent(familyId())}`, { method: "DELETE" });
}
