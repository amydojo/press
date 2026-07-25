import { systemDiagnosticsSchema, type SystemDiagnostics } from "@/lib/system-contract";

export async function loadSystemDiagnostics(): Promise<SystemDiagnostics> {
  const response = await fetch("/api/system/health", {
    cache: "no-store",
    headers: { accept: "application/json" },
  });
  const payload: unknown = await response.json().catch(() => undefined);
  return systemDiagnosticsSchema.parse(payload);
}
