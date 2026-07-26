import type { components } from "@press/contracts";

export type PressingResponse = components["schemas"]["PressingResponse"];
export type PressingRecord = components["schemas"]["PressingRecord"];
export type CreatePressingRequest = components["schemas"]["CreatePressingRequest"];
export type PressingStatus = components["schemas"]["PressingStatus"];

const API_BASE = process.env.NEXT_PUBLIC_PRESS_API_BASE_URL ?? "http://localhost:8000";

async function parseResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    const message = payload?.detail?.message ?? `PRESS API returned ${response.status}`;
    throw new Error(message);
  }
  return response.json() as Promise<T>;
}

export async function createPressing(input: CreatePressingRequest): Promise<PressingResponse> {
  return parseResponse(
    await fetch(`${API_BASE}/v1/pressings`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(input),
    }),
  );
}

export async function listPressings(): Promise<PressingResponse[]> {
  return parseResponse(
    await fetch(`${API_BASE}/v1/pressings`, { cache: "no-store" }),
  );
}

export async function getPressing(id: string): Promise<PressingResponse> {
  return parseResponse(
    await fetch(`${API_BASE}/v1/pressings/${encodeURIComponent(id)}`, { cache: "no-store" }),
  );
}

export async function deletePressing(id: string): Promise<void> {
  await parseResponse(
    await fetch(`${API_BASE}/v1/pressings/${encodeURIComponent(id)}`, { method: "DELETE" }),
  );
}
