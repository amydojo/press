import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { PressingObject } from "./pressing-object";

const pressing = {
  id: "pressing-1",
  serialNumber: "P-0027",
  status: "ready",
  idempotencyKeyHash: "hash",
  progressEventCount: 0,
  source: {
    sourceType: "url",
    submittedUrl: "https://example.com/story",
    canonicalUrl: "https://example.com/story",
    domain: "example.com",
    title: "A story",
    capturedAt: "2026-07-26T12:00:00Z",
  },
  anchors: {
    submittedSourceIdentity: "https://example.com/story",
    selectedFragment: "Design is paced through rhythm.",
    personalNote: "The pacing feels like music.",
  },
  understanding: { archetype: "scene", contentType: "article", density: "quiet", atmosphere: [], generationBrief: "", motif: "", palette: ["#8d9c91"] },
  final: null,
} as const;

describe("PressingObject", () => {
  it("renders exact front anchors without relying on generated text", () => {
    render(<PressingObject pressing={pressing} />);
    expect(screen.getByText("Design is paced through rhythm.")).toBeInTheDocument();
    expect(screen.getByText("P-0027")).toBeInTheDocument();
    expect(screen.getByText("example.com")).toBeInTheDocument();
  });

  it("renders exact back metadata when generated media is missing", () => {
    render(<PressingObject pressing={pressing} back />);
    expect(screen.getByText("The pacing feels like music.")).toBeInTheDocument();
    expect(screen.getByText("Pressed from the internet")).toBeInTheDocument();
  });
});
