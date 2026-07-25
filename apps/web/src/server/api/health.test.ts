import { afterEach, describe, expect, it, vi } from "vitest";

import { fetchGenerationHealth } from "@/server/api/health";

afterEach(() => vi.unstubAllGlobals());

describe("typed generation API health client", () => {
  it("parses the real FastAPI health response shape", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            status: "ok",
            service: "press-generation-api",
            version: "0.1.0",
            environment: "test",
            timestamp: "2026-07-24T12:00:00+00:00",
          }),
          { status: 200, headers: { "content-type": "application/json" } },
        ),
      ),
    );

    await expect(fetchGenerationHealth("typed-contract-test")).resolves.toMatchObject({
      status: "ok",
      service: "press-generation-api",
    });
  });

  it("maps malformed payloads to a stable application error", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ status: "probably" }), { status: 200 }),
      ),
    );

    await expect(fetchGenerationHealth("malformed-test")).rejects.toMatchObject({
      kind: "malformed_response",
    });
  });

  it("maps network failures to a stable application error", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("connection refused")));

    await expect(fetchGenerationHealth("network-test")).rejects.toMatchObject({
      kind: "network_error",
    });
  });
});
