import { z } from "zod";

export const PRESSING_STORAGE_KEY = "press:pressings:v1";
export const MIN_SOURCE_LENGTH = 12;
export const MAX_SOURCE_LENGTH = 1200;

export const pressingStatuses = [
  "registered",
  "reading",
  "interpreting",
  "constructing",
  "rendering",
  "sealing",
  "ready",
  "kept",
  "failed",
] as const;

export type PressingStatus = (typeof pressingStatuses)[number];

const sourceSchema = z.object({
  type: z.literal("text"),
  content: z.string().min(MIN_SOURCE_LENGTH).max(MAX_SOURCE_LENGTH),
  registeredAt: z.string().datetime(),
});

const resultSchema = z.object({
  title: z.string().min(1),
  archetype: z.string().min(1),
  interpretation: z.string().min(1),
  artifactUrl: z.string().min(1),
});

export const pressingSchema = z.object({
  id: z.string().min(8),
  number: z.string().regex(/^P-\d{6}$/),
  status: z.enum(pressingStatuses),
  source: sourceSchema,
  result: resultSchema.optional(),
  createdAt: z.string().datetime(),
  keptAt: z.string().datetime().optional(),
  failedFrom: z.enum(["reading", "interpreting", "constructing", "rendering", "sealing"]).optional(),
});

export type Pressing = z.infer<typeof pressingSchema>;

const envelopeSchema = z.object({
  version: z.literal(1),
  records: z.array(z.unknown()),
});

export const fixtureResult = {
  title: "Decision Appliance",
  archetype: "Reluctant machine",
  interpretation:
    "The fragment treats an ordinary appliance as a tired living system. PRESS preserved the hesitation rather than the refrigerator itself.",
  artifactUrl: "fixture://decision-appliance/v1",
} as const;

export const processingPhases = [
  { status: "reading", label: "Reading the fragment" },
  { status: "interpreting", label: "Locating the pressure point" },
  { status: "constructing", label: "Constructing the object" },
  { status: "rendering", label: "Rendering the pressing" },
  { status: "sealing", label: "Sealing" },
] as const;

const nextStatus: Partial<Record<PressingStatus, PressingStatus>> = {
  registered: "reading",
  reading: "interpreting",
  interpreting: "constructing",
  constructing: "rendering",
  rendering: "sealing",
  sealing: "ready",
  ready: "kept",
};

export class PressingTransitionError extends Error {
  constructor(from: PressingStatus, to: PressingStatus) {
    super(`Invalid pressing transition: ${from} -> ${to}`);
    this.name = "PressingTransitionError";
  }
}

export function normalizeSource(value: string): string {
  return value.replace(/\r\n?/g, "\n").split("\n").map((line) => line.trim()).join("\n").trim();
}

export function validateSource(value: string): string | null {
  const normalized = normalizeSource(value);
  if (!normalized) return "Enter the fragment that made you stop.";
  if (normalized.length < MIN_SOURCE_LENGTH) return `Use at least ${MIN_SOURCE_LENGTH} characters.`;
  if (normalized.length > MAX_SOURCE_LENGTH) return `Keep the fragment under ${MAX_SOURCE_LENGTH} characters.`;
  return null;
}

function randomId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) return crypto.randomUUID();
  return `pressing-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

function pressingNumber(now: Date, id: string): string {
  const datePart = `${String(now.getUTCMonth() + 1).padStart(2, "0")}${String(now.getUTCDate()).padStart(2, "0")}`;
  const hash = Array.from(id).reduce((sum, char) => (sum + char.charCodeAt(0)) % 100, 0);
  return `P-${datePart}${String(hash).padStart(2, "0")}`;
}

export function createPressing(sourceContent: string, now = new Date()): Pressing {
  const content = normalizeSource(sourceContent);
  const error = validateSource(content);
  if (error) throw new Error(error);
  const id = randomId();
  const timestamp = now.toISOString();
  return pressingSchema.parse({
    id,
    number: pressingNumber(now, id),
    status: "registered",
    source: { type: "text", content, registeredAt: timestamp },
    createdAt: timestamp,
  });
}

export function transitionPressing(pressing: Pressing, to: PressingStatus, now = new Date()): Pressing {
  if (pressing.status === to && (to === "kept" || to === "ready")) return pressing;
  if (nextStatus[pressing.status] !== to) throw new PressingTransitionError(pressing.status, to);
  const patch: Partial<Pressing> = { status: to };
  if (to === "ready") patch.result = fixtureResult;
  if (to === "kept") patch.keptAt = pressing.keptAt ?? now.toISOString();
  return pressingSchema.parse({ ...pressing, ...patch, failedFrom: undefined });
}

export function failPressing(pressing: Pressing): Pressing {
  if (!["reading", "interpreting", "constructing", "rendering", "sealing"].includes(pressing.status)) {
    throw new PressingTransitionError(pressing.status, "failed");
  }
  return pressingSchema.parse({ ...pressing, failedFrom: pressing.status, status: "failed" });
}

export function retryPressing(pressing: Pressing): Pressing {
  if (pressing.status !== "failed") throw new PressingTransitionError(pressing.status, "reading");
  return pressingSchema.parse({ ...pressing, status: "reading", failedFrom: undefined });
}

export interface StorageLike {
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
  removeItem(key: string): void;
}

export type ParseResult = { records: Pressing[]; malformed: boolean };

export function parseStoredPressings(raw: string | null): ParseResult {
  if (!raw) return { records: [], malformed: false };
  try {
    const envelope = envelopeSchema.parse(JSON.parse(raw));
    let malformed = false;
    const records = envelope.records.flatMap((record) => {
      const parsed = pressingSchema.safeParse(record);
      if (!parsed.success) {
        malformed = true;
        return [];
      }
      return [parsed.data];
    });
    return { records, malformed };
  } catch {
    return { records: [], malformed: true };
  }
}

export class PressingRepository {
  constructor(private readonly storage: StorageLike) {}

  private snapshot(): ParseResult {
    return parseStoredPressings(this.storage.getItem(PRESSING_STORAGE_KEY));
  }

  private write(records: Pressing[]): void {
    this.storage.setItem(PRESSING_STORAGE_KEY, JSON.stringify({ version: 1, records }));
  }

  list(): Pressing[] {
    return this.snapshot().records.sort((a, b) => a.createdAt.localeCompare(b.createdAt) || a.id.localeCompare(b.id));
  }

  listKept(): Pressing[] {
    return this.snapshot().records
      .filter((record) => record.status === "kept" && Boolean(record.keptAt))
      .sort((a, b) => (b.keptAt ?? "").localeCompare(a.keptAt ?? "") || b.createdAt.localeCompare(a.createdAt) || a.id.localeCompare(b.id));
  }

  read(id: string): Pressing | null {
    return this.snapshot().records.find((record) => record.id === id) ?? null;
  }

  create(content: string): Pressing {
    const record = createPressing(content);
    const records = this.snapshot().records;
    this.write([...records, record]);
    return record;
  }

  save(record: Pressing): Pressing {
    const validated = pressingSchema.parse(record);
    const records = this.snapshot().records;
    const index = records.findIndex((item) => item.id === validated.id);
    this.write(index < 0 ? [...records, validated] : records.map((item) => (item.id === validated.id ? validated : item)));
    return validated;
  }

  advance(id: string, to: PressingStatus): Pressing {
    const current = this.read(id);
    if (!current) throw new Error("Pressing not found");
    return this.save(transitionPressing(current, to));
  }

  keep(id: string): Pressing {
    const current = this.read(id);
    if (!current) throw new Error("Pressing not found");
    if (current.status === "kept") return current;
    return this.save(transitionPressing(current, "kept"));
  }

  retry(id: string): Pressing {
    const current = this.read(id);
    if (!current) throw new Error("Pressing not found");
    return this.save(retryPressing(current));
  }

  remove(id: string): void {
    this.write(this.snapshot().records.filter((record) => record.id !== id));
  }

  clearForTest(): void {
    this.storage.removeItem(PRESSING_STORAGE_KEY);
  }

  hasMalformedData(): boolean {
    return this.snapshot().malformed;
  }
}

export function browserRepository(): PressingRepository {
  if (typeof window === "undefined") throw new Error("Browser storage is unavailable");
  return new PressingRepository(window.localStorage);
}
