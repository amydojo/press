import { render, screen } from "@testing-library/react";
import { expect, it } from "vitest";

import HomePage from "@/app/page";

it("renders the PRESS product identity and primary journey", () => {
  render(<HomePage />);

  expect(screen.getByRole("link", { name: "PRESS home" })).toHaveAttribute("href", "/");
  expect(screen.getByRole("heading", { name: "Keep what made you stop." })).toBeInTheDocument();
  expect(screen.getByText("A preservation instrument for the internet")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Press something" })).toHaveAttribute("href", "/press/new");
  expect(screen.getByRole("region", { name: "How PRESS works" })).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "Capture" })).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "Press" })).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "Keep" })).toBeInTheDocument();
});
