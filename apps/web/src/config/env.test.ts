import { describe, expect, it } from "vitest";

import { parsePublicEnvironment, parseServerEnvironment } from "@/config/env";

describe("environment parsing", () => {
  it("accepts safe local defaults", () => {
    expect(parseServerEnvironment({})).toEqual({
      API_BASE_URL: "http://localhost:8000",
      PRESS_ENV: "development",
      PRESS_VERSION: "0.1.0",
    });
  });

  it("rejects a non-http API base URL", () => {
    expect(() => parseServerEnvironment({ API_BASE_URL: "file:///tmp/api" })).toThrow();
  });

  it("rejects an invalid public app URL", () => {
    expect(() => parsePublicEnvironment({ NEXT_PUBLIC_APP_URL: "javascript:alert(1)" })).toThrow();
  });
});
