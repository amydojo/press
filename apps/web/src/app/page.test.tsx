import { render, screen } from "@testing-library/react";

import HomePage from "@/app/page";

it("renders the PRESS product identity and foundation disclosure", () => {
  render(<HomePage />);

  expect(screen.getByRole("heading", { name: "PRESS" })).toBeInTheDocument();
  expect(screen.getByText("Keep what made you stop.")).toBeInTheDocument();
  expect(screen.getByText("Foundation in progress.")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Open system diagnostics" })).toHaveAttribute(
    "href",
    "/system",
  );
});
