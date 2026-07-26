import type { components } from "@press/contracts";
import { z } from "zod";

import { getServerEnvironment } from "@/config/env";
import { PressApiError } from "@/server/api/errors";

type HealthResponse = components["schemas"]["HealthResponse"];

const healthResponseSchema = z.object({
  status: z.literal("ok"),
  service: z.literal("press-generation-api"),
  version: z.string().min(1),
  environment: z.string().min(1),
  timestamp: z.iso.datetime({ offset: true }),
  liveProviderConfigured: z.boolean(),
  durableStorageConfigured: z.boolean(),
});

export async function fetchGenerationHealth(requestId: string): Promise<HealthResponse> {
  const environment = getServerEnvironment();
  let response: Response;

  try {
    response = await fetch(new URL("/healthz", environment.API_BASE_URL), {
      cache: "no-store",
      headers: { "x-request-id": requestId },
      signal: AbortSignal.timeout(4_000),
    });
  } catch (error) {
    throw new PressApiError(
      "network_error",
      error instanceof Error ? error.message : "Generation API request failed",
    );
  }

  if (!response.ok) {
    throw new PressApiError(
      "http_error",
      `Generation API returned HTTP ${response.status}`,
      response.status,
    );
  }

  const payload: unknown = await response.json().catch(() => undefined);
  const parsed = healthResponseSchema.safeParse(payload);
  if (!parsed.success) {
    throw new PressApiError("malformed_response", "Generation API response did not match the contract");
  }

  return parsed.data satisfies HealthResponse;
}
