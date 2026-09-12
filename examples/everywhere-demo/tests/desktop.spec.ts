import { test, expect, _electron as electron } from "@playwright/test";
import path from "node:path";

test("native desktop shares a phone conversation and responsive surfaces render", async ({
  request,
  page,
}) => {
  const r = await request.post("/api/sessions");
  const { id } = await r.json();
  await page.goto(`/phone#session=${id}`);
  await page
    .getByRole("button", {
      name: "Find work sneakers under $120, US 9",
      exact: true,
    })
    .click();
  await expect(
    page.getByText("I’ve saved your brief:", { exact: false }),
  ).toBeVisible();
  const desktopEnv = { ...process.env };
  delete desktopEnv.ELECTRON_RUN_AS_NODE;
  const desktop = await electron.launch({
    args: [path.resolve("desktop/main.cjs")],
    env: {
      ...desktopEnv,
      ONEAGENT_URL: `http://127.0.0.1:3107/desktop#session=${id}`,
    },
  });
  try {
    const window = await desktop.firstWindow();
    await expect(
      window.getByText("I’ve saved your brief:", { exact: false }),
    ).toBeVisible();
    await window
      .getByRole("button", { name: "What do you remember?", exact: true })
      .click();
    await expect(
      page.getByText("Your brief is US 9, a $120 budget", { exact: false }),
    ).toBeVisible();
    await window.screenshot({ path: "test-results/native-desktop.png" });
  } finally {
    await desktop.close();
  }
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(`/#session=${id}`);
  await expect(
    page.getByRole("heading", { name: "Different apps." }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await page.getByRole("button", { name: "STRIDE", exact: true }).click();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await page.setViewportSize({ width: 1440, height: 1150 });
  await page.screenshot({
    path: "test-results/stride-preview.png",
    fullPage: true,
  });
  const network = await (await request.get("/api/network")).json();
  if (network.addresses.length) {
    await page.goto(`${network.addresses[0]}/phone#session=${id}`);
    await page
      .getByRole("button", { name: "What do you remember?", exact: true })
      .click();
    await expect
      .poll(async () => {
        const state = await (await request.get(`/api/sessions/${id}`)).json();
        return state.messages.filter(
          (m: { content: string; role: string }) =>
            m.role === "assistant" &&
            m.content.startsWith("Your brief is US 9"),
        ).length;
      })
      .toBe(2);
  }
});
