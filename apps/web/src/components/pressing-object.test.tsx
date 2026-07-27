import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { PressingRecord } from "@/lib/pressings";

import { PressingObject } from "./pressing-object";

const pressing: PressingRecord = {
  id: "pressing-1",
  serialNumber: "P-0027",
  status: "ready",
  idempotencyKeyHash: "hash",
  progressEventCount: 0,
  source: {
    sourceType: "url",
    submittedSourceIdentity: "https://example.com/story",
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
};

describe("PressingObject", () => {
  it("renders exact authoritative anchors on both faces", () => {
    render(<PressingObject pressing={pressing} back />);
    expect(screen.getByText("Design is paced through rhythm.")).toBeInTheDocument();
    expect(screen.getByText("The pacing feels like music.")).toBeInTheDocument();
    expect(screen.getAllByText("P-0027").length).toBeGreaterThan(0);
    expect(screen.getByLabelText("Back of P-0027 from example.com")).toBeInTheDocument();
  });

  it("offers an explicit side-change callback in addition to pointer inspection", () => {
    const onSideChange = vi.fn();
    render(<PressingObject pressing={pressing} interactive onSideChange={onSideChange} />);
    fireEvent.doubleClick(screen.getByLabelText("Front of P-0027 from example.com"));
    expect(onSideChange).toHaveBeenCalledWith(true);
  });

  it("renders a deliberate internal fallback rather than a broken media element", () => {
    const { container } = render(<PressingObject pressing={pressing} />);
    expect(container.querySelector(".pressing-object__fallback")).toBeInTheDocument();
    expect(container.querySelector("img")).not.toBeInTheDocument();
  });
});
