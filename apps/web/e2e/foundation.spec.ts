import { expect, test } from "@playwright/test";

test("PRESS foundation reaches the live generation API", async ({ page }) => {
  const consoleErrors: string[] = [];
  page.on("console", (message) => {
    if (message.type() === "error") consoleErrors.push(message.text());
  });

  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Keep what made you stop." })).toBeVisible();

  await page.goto("/system");
  await expect(page).toHaveURL(/\/system$/);
  await expect(page.getByRole("heading", { name: "Foundation online." })).toBeVisible();
  await expect(page.getByText("Web status")).toBeVisible();
  await expect(page.getByText("Generation API status")).toBeVisible();
  await expect(page.getByText("healthy")).toHaveCount(2);

  await page.screenshot({ path: "test-results/system-diagnostics.png", fullPage: true });
  expect(consoleErrors).toEqual([]);
});