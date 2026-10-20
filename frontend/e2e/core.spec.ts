import { test, expect } from "@playwright/test";
test("delivery preview, weekly payout and ledger use the real API", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Record a delivery" })).toBeVisible();
  await page.getByLabel("Crop", { exact: true }).selectOption({ label: "Maize" });
  await page.getByLabel("Gross weight").fill("100");
  await page.getByLabel("Moisture · %").fill("17.6");
  await expect(page.getByText("Price found", { exact: true })).toBeVisible();
  await page.screenshot({ path: "test-results/desktop-preview.png", fullPage: true });
  await expect(page.locator(".total strong")).toHaveText("₹2,425.00");
  await page.getByRole("button", { name: "Save delivery" }).click();
  await expect(page.getByRole("status")).toContainText("saved");
  await page.getByRole("button", { name: "Weekly payouts" }).click();
  await page.getByRole("button", { name: "Generate / refresh draft" }).click();
  await expect(page.getByRole("button", { name: "Finalise statement" })).toBeVisible();
  await page.getByRole("button", { name: "Finalise statement" }).click();
  await page.getByRole("button", { name: "Confirm finalisation" }).click();
  await expect(page.getByRole("button", { name: "Mark as paid" })).toBeVisible();
  await page.getByRole("button", { name: "Mark as paid" }).click();
  await expect(page.locator(".badge.paid")).toHaveCount(2);
  await page.getByRole("button", { name: "Farmer ledger" }).click();
  await expect(page.getByRole("heading", { name: "Farmer account", exact: true })).toBeVisible();
  await expect(page.locator(".account-banner")).toContainText("₹4,272.50");
  await page.getByRole("button", { name: "Price history" }).click();
  await expect(page.getByRole("heading", { name: "Effective price history" })).toBeVisible();
  await page.getByLabel("Crop", { exact: true }).selectOption({ label: "Maize" });
  await expect(page.locator("tbody")).toContainText("₹25.00");
});
test("phone layout keeps delivery entry within viewport", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Record a delivery" })).toBeVisible();
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth),
  ).toBeTruthy();
  await page.screenshot({ path: "test-results/mobile.png", fullPage: true });
});
