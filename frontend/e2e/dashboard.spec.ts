import { expect, test } from "@playwright/test";

const expectedGridColumns: Record<string, number> = {
  desktop: 12,
  tablet: 6,
  mobile: 1,
};

test("loads production built JS and expands dashboard history responsively", async ({ page }, testInfo) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  const scriptResponse = page.waitForResponse((response) => (
    response.request().resourceType() === "script"
    && new URL(response.url()).pathname.startsWith("/static/app/assets/")
  ));

  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Garmin Training Dashboard" })).toBeVisible();
  expect((await scriptResponse).ok()).toBe(true);

  const metrics = page.getByRole("region", { name: "Current metrics" });
  const columns = await metrics.evaluate((element) => (
    getComputedStyle(element).gridTemplateColumns.split(" ").filter(Boolean).length
  ));
  expect(columns).toBe(expectedGridColumns[testInfo.project.name]);

  const card = metrics.locator("article").filter({ hasText: "Activity volume" });
  const supporting = card.getByText(/activit(?:y|ies) · \d/);
  await expect(supporting).toBeVisible();
  const toggle = card.getByRole("button", { name: /activity volume/i });
  if (testInfo.project.name === "mobile") {
    expect((await toggle.boundingBox())?.height).toBeGreaterThanOrEqual(44);
  }

  const trendResponse = page.waitForResponse((response) => (
    new URL(response.url()).pathname === "/api/dashboard/trends"
  ));
  await toggle.click();
  await expect(toggle).toHaveAttribute("aria-expanded", "true");
  await expect(supporting).toBeVisible();
  await expect(page.getByLabel("Trend period")).toBeVisible();

  const response = await trendResponse;
  expect(response.ok()).toBe(true);
  const params = new URL(response.url()).searchParams;
  const start = Date.parse(`${params.get("start")}T00:00:00Z`);
  const end = Date.parse(`${params.get("end")}T00:00:00Z`);
  expect((end - start) / 86_400_000).toBe(84);
  await expect(card.getByRole("img", { name: "Activity volume trend" })).toBeVisible();

  const transitionDuration = await card.evaluate((element) => getComputedStyle(element).transitionDuration);
  expect(transitionDuration).toBe("0s");
});
