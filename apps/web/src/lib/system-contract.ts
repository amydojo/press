import { z } from "zod";

const releaseIdentity = {
  commitSha: z.string().min(1),
};

export const systemDiagnosticsSchema = z.discriminatedUnion("apiStatus", [
  z.object({
    ...releaseIdentity,
    webStatus: z.literal("ok"),
    apiStatus: z.literal("healthy"),
    apiVersion: z.string(),
    environment: z.string(),
    contractVersion: z.string(),
    timestamp: z.string(),
    requestId: z.string(),
  }),
  z.object({
    ...releaseIdentity,
    webStatus: z.literal("ok"),
    apiStatus: z.literal("unreachable"),
    reason: z.literal("network_error").or(z.literal("http_error")),
    requestId: z.string(),
  }),
  z.object({
    ...releaseIdentity,
    webStatus: z.literal("ok"),
    apiStatus: z.literal("malformed"),
    reason: z.literal("malformed_response"),
    requestId: z.string(),
  }),
]);

export type SystemDiagnostics = z.infer<typeof systemDiagnosticsSchema>;
