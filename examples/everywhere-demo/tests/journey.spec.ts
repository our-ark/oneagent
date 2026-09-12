import { test, expect } from "@playwright/test";

test("phone brief, source-bound store replies, comparison, approval, and cross-device receipt", async ({
  page,
  browser,
  request,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  const response = await request.post("/api/sessions");
  const { id } = await response.json();
  await page.goto(`/#session=${id}`);
  await expect(
    page.getByRole("heading", { name: "Different apps." }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Phone", exact: true }).click();
  await page
    .getByRole("button", {
      name: "Find work sneakers under $120, US 9",
      exact: true,
    })
    .click();
  await expect(
    page.getByText("I’ve saved your brief:", { exact: false }),
  ).toBeVisible();
  await page.getByRole("button", { name: /DAYFORM Day One/ }).click();
  await page
    .getByRole("button", {
      name: "Will these be comfortable on my walk?",
      exact: true,
    })
    .click();
  await page.getByRole("button", { name: "STRIDE", exact: true }).click();
  await expect(
    page.getByText("Day One is a good match for your commute:", {
      exact: false,
    }),
  ).toHaveCount(0);
  // Wait for the first store's reply to finish before the second turn.
  await expect
    .poll(async () => {
      const r = await request.get(`/api/sessions/${id}`);
      return (await r.json()).messages.filter(
        (m: any) => m.role === "assistant",
      ).length;
    })
    .toBe(2);
  await page
    .getByRole("button", {
      name: "How does this compare with the first pair?",
      exact: true,
    })
    .click();
  await expect(
    page.getByText("Compared with Day One, Arc 02 is $14 more.", {
      exact: false,
    }),
  ).toBeVisible();
  const second = await browser.newContext({
    viewport: { width: 390, height: 844 },
  });
  const phone = await second.newPage();
  await phone.goto(`/phone#session=${id}`);
  await expect(
    phone.getByText("Compared with Day One, Arc 02 is $14 more.", {
      exact: false,
    }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "DAYFORM", exact: true })
    .first()
    .click();
  await expect(
    page.getByText("Day One is a good match for your commute:", {
      exact: false,
    }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Order this pair", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "Approve demo order · $107.80" }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Approve demo order · $107.80" })
    .click();
  await expect(
    page.getByText("ORDER CONFIRMED", { exact: true }),
  ).toBeVisible();
  await expect(
    phone.getByText("ORDER CONFIRMED", { exact: true }),
  ).toBeVisible();
  await phone.reload();
  await expect(
    phone.getByText("ORDER CONFIRMED", { exact: true }),
  ).toBeVisible();
  expect(
    await phone.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({
    path: "test-results/completed-dayform.png",
    fullPage: true,
  });
  await phone.screenshot({
    path: "test-results/phone-receipt.png",
    fullPage: true,
  });
  expect(errors).toEqual([]);
  await second.close();
});

test("revocation is enforced and disclosure is explicit", async ({
  page,
  request,
}) => {
  const response = await request.post("/api/sessions");
  const { id } = await response.json();
  await page.goto(`/#session=${id}`);
  await page
    .getByRole("button", { name: "Open connections", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Revoke DAYFORM", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "Connect DAYFORM", exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Close dialog", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Connection paused" }),
  ).toBeVisible();
  await expect(
    page.getByRole("textbox", { name: "Message Bob" }),
  ).toBeDisabled();
  const catalog = await request.get(`/api/sessions/${id}/catalog/dayform`);
  expect(catalog.status()).toBe(403);
  await page
    .getByRole("button", { name: "Manage connections", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Connect DAYFORM", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "Revoke DAYFORM", exact: true }),
  ).toBeVisible();
  await page
    .getByRole("checkbox", {
      name: "Share my budget for this store’s own filtering",
    })
    .first()
    .click();
  await expect(
    page
      .getByRole("checkbox", {
        name: "Share my budget for this store’s own filtering",
      })
      .first(),
  ).toBeChecked();
  await expect
    .poll(async () => {
      const r = await request.get(`/api/sessions/${id}/catalog/dayform`);
      return (await r.json()).authorizedContext.budget;
    })
    .toBe(120);
});
