// Playwright smoke spec for the Family Cards demo page.
// The demo runs OPEN on plain static hosting (no gate): owner view,
// both fake kids behind tabs, note box present but disabled.
// The data asserted here is the demo's checked-in fake data
// (emma.json / noah.json) — update the expectations when the fake
// data changes. Runs in CI via smoke.yml, which serves the repo
// root locally and points SMOKE_BASE_URL at it.
const { test, expect } = require("@playwright/test");

const BASE = process.env.SMOKE_BASE_URL || "http://127.0.0.1:8901/";

test.beforeEach(async ({ page }) => {
  await page.goto(BASE);
});

test("page loads with the demo banner and both kid tabs", async ({ page }) => {
  await expect(page).toHaveTitle("My next two weeks");
  await expect(page.locator("#demo-banner")).toBeVisible();
  const tabs = page.locator("#tabs button");
  await expect(tabs).toHaveCount(2);
  await expect(tabs.nth(0)).toHaveText("Emma");
  await expect(tabs.nth(1)).toHaveText("Noah");
});

test("Emma's card renders entries from her data", async ({ page }) => {
  await expect(page.locator("#heading")).toHaveText("Emma — next two weeks");
  await expect(
    page.locator(".entry", { hasText: "Soccer practice" })
  ).toBeVisible();
  // The CHANGED example: a third-party pickup, named and tagged.
  const dance = page.locator(".entry", { hasText: "Dance class" });
  await expect(dance.locator(".changed")).toHaveText("CHANGED");
  await expect(
    dance.locator(".leg", { hasText: "Grandma picks you up" })
  ).toBeVisible();
});

test("switching to Noah's tab renders his card", async ({ page }) => {
  await page.locator("#tabs button", { hasText: "Noah" }).click();
  await expect(page.locator("#heading")).toHaveText("Noah — next two weeks");
  await expect(
    page.locator(".entry", { hasText: "Robotics club" })
  ).toBeVisible();
});

test("the note box is present but disabled in demo mode", async ({ page }) => {
  const box = page.locator(".notebox");
  await expect(box).toBeVisible();
  await expect(box.locator("textarea")).toBeDisabled();
  await expect(box.getByText("Demo — notes are turned off here; nothing is sent or stored.")).toBeVisible();
});
