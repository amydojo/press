import { describe, expect, it } from "vitest";

import {
  PressingRepository,
  PressingTransitionError,
  createPressing,
  failPressing,
  fixtureResult,
  normalizeSource,
  parseStoredPressings,
  retryPressing,
  transitionPressing,
  type StorageLike,
} from "./pressings";

class MemoryStorage implements StorageLike {
  private values = new Map<string, string>();
  getItem(key: string) { return this.values.get(key) ?? null; }
  setItem(key: string, value: string) { this.values.set(key, value); }
  removeItem(key: string) { this.values.delete(key); }
}

const source = "The apartment was silent except for the refrigerator deciding whether to continue.";

describe("pressing domain", () => {
  it("normalizes surrounding whitespace while preserving line breaks", () => {
    expect(normalizeSource("  First line  \r\n  Second line  ")).toBe("First line\nSecond line");
  });

  it("creates stable-shaped registered records", () => {
    const pressing = createPressing(source, new Date("2026-07-25T12:00:00.000Z"));
    expect(pressing.status).toBe("registered");
    expect(pressing.number).toMatch(/^P-\d{6}$/);
    expect(pressing.source.content).toBe(source);
  });

  it("guards and completes the canonical transition order", () => {
    let pressing = createPressing(source);
    for (const status of ["reading", "interpreting", "constructing", "rendering", "sealing", "ready"] as const) {
      pressing = transitionPressing(pressing, status);
    }
    expect(pressing.result).toEqual(fixtureResult);
    expect(() => transitionPressing(pressing, "reading")).toThrow(PressingTransitionError);
  });

  it("retries a failed pressing without changing its identity", () => {
    const reading = transitionPressing(createPressing(source), "reading");
    const failed = failPressing(reading);
    const retried = retryPressing(failed);
    expect(retried.id).toBe(reading.id);
    expect(retried.status).toBe("reading");
  });
});

describe("pressing persistence", () => {
  it("creates, reloads, updates, and keeps idempotently", () => {
    const storage = new MemoryStorage();
    const repository = new PressingRepository(storage);
    const created = repository.create(source);
    expect(new PressingRepository(storage).read(created.id)?.status).toBe("registered");
    repository.advance(created.id, "reading");
    repository.advance(created.id, "interpreting");
    repository.advance(created.id, "constructing");
    repository.advance(created.id, "rendering");
    repository.advance(created.id, "sealing");
    repository.advance(created.id, "ready");
    const once = repository.keep(created.id);
    const twice = repository.keep(created.id);
    expect(twice.keptAt).toBe(once.keptAt);
    expect(repository.listKept()).toHaveLength(1);
  });

  it("recovers from malformed envelopes and records", () => {
    expect(parseStoredPressings("not-json")).toEqual({ records: [], malformed: true });
    const parsed = parseStoredPressings(JSON.stringify({ version: 1, records: [{ nope: true }] }));
    expect(parsed.records).toEqual([]);
    expect(parsed.malformed).toBe(true);
  });

  it("orders kept records deterministically by keptAt descending", () => {
    const storage = new MemoryStorage();
    const repository = new PressingRepository(storage);
    const first = createPressing(source, new Date("2026-07-25T10:00:00.000Z"));
    const second = createPressing(source, new Date("2026-07-25T11:00:00.000Z"));
    repository.save({ ...first, status: "kept", result: fixtureResult, keptAt: "2026-07-25T12:00:00.000Z" });
    repository.save({ ...second, status: "kept", result: fixtureResult, keptAt: "2026-07-25T13:00:00.000Z" });
    expect(repository.listKept().map((item) => item.id)).toEqual([second.id, first.id]);
  });
});
