import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { SystemDiagnostics } from "@/components/system-diagnostics";
import { loadSystemDiagnostics } from "@/lib/system-client";

vi.mock("@/lib/system-client", () => ({
  loadSystemDiagnostics: vi.fn(),
}));

const mockedLoad = vi.mocked(loadSystemDiagnostics);
const commitSha = "test-commit-sha";

describe("SystemDiagnostics", () => {
  beforeEach(() => {
    mockedLoad.mockReset();
  });

  it("shows loading before the diagnostics resolve", () => {
    mockedLoad.mockImplementation(() => new Promise(() => undefined));
    render(<SystemDiagnostics />);
    expect(screen.getByText("Generation API status: loading")).toBeInTheDocument();
  });

  it("shows a healthy live API state", async () => {
    mockedLoad.mockResolvedValue({
      webStatus: "ok",
      apiStatus: "healthy",
      apiVersion: "0.1.0",
      environment: "test",
      contractVersion: "0.1.0",
      timestamp: "2026-07-24T12:00:00+00:00",
      requestId: "request-healthy",
      commitSha,
    });
    render(<SystemDiagnostics />);

    expect(await screen.findByText("Foundation online.")).toBeInTheDocument();
    expect(screen.getAllByText("healthy")).toHaveLength(2);
  });

  it("shows the truthful unreachable state", async () => {
    mockedLoad.mockResolvedValue({
      webStatus: "ok",
      apiStatus: "unreachable",
      reason: "network_error",
      requestId: "request-unreachable",
      commitSha,
    });
    render(<SystemDiagnostics />);

    expect(await screen.findByText("Generation API unreachable.")).toBeInTheDocument();
    expect(screen.getByText(/No healthy API result is being faked/)).toBeInTheDocument();
  });

  it("shows a malformed API response state", async () => {
    mockedLoad.mockResolvedValue({
      webStatus: "ok",
      apiStatus: "malformed",
      reason: "malformed_response",
      requestId: "request-malformed",
      commitSha,
    });
    render(<SystemDiagnostics />);

    expect(await screen.findByText("Generation API response malformed.")).toBeInTheDocument();
  });

  it("handles a malformed internal diagnostics response", async () => {
    mockedLoad.mockImplementation(async () => {
      throw new Error("invalid internal payload");
    });
    render(<SystemDiagnostics />);

    expect(await screen.findByText("Diagnostics response malformed.")).toBeInTheDocument();
  });
});
