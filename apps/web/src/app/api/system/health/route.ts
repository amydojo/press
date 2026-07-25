import { NextResponse } from "next/server";

import { getServerEnvironment } from "@/config/env";
import type { SystemDiagnostics } from "@/lib/system-contract";
import { PressApiError } from "@/server/api/errors";
import { fetchGenerationHealth } from "@/server/api/health";

export const dynamic = "force-dynamic";

export async function GET(): Promise<NextResponse<SystemDiagnostics>> {
  const requestId = crypto.randomUUID();
  const webEnvironment = getServerEnvironment();

  try {
    const health = await fetchGenerationHealth(requestId);
    return NextResponse.json({
      webStatus: "ok",
      apiStatus: "healthy",
      apiVersion: health.version,
      environment: health.environment,
      contractVersion: webEnvironment.PRESS_VERSION,
      timestamp: health.timestamp,
      requestId,
    });
  } catch (error) {
    if (error instanceof PressApiError && error.kind === "malformed_response") {
      return NextResponse.json(
        {
          webStatus: "ok",
          apiStatus: "malformed",
          reason: "malformed_response",
          requestId,
        },
        { status: 502 },
      );
    }

    const reason = error instanceof PressApiError && error.kind === "http_error"
      ? "http_error"
      : "network_error";
    return NextResponse.json(
      {
        webStatus: "ok",
        apiStatus: "unreachable",
        reason,
        requestId,
      },
      { status: 503 },
    );
  }
}
