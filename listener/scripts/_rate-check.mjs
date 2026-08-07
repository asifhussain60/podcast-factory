import { chromium } from "playwright";
import { setUp, tearDown, fill } from "./fixtures.mjs";

const BASE = "http://localhost:5273";
const { cookies, book, episode } = await setUp();
const url = BASE + fill("/book/:slug", book, null, episode);

const browser = await chromium.launch();
const ctx = await browser.newContext({
  viewport: { width: 1440, height: 900 },
  extraHTTPHeaders: { Cookie: cookies.reader },
});
const page = await ctx.newPage();
await page.goto(url, { waitUntil: "networkidle" });

// Start something playing, then choose a speed.
await page.click(".pf-tabset__tab:nth-child(2)").catch(() => {});
await page.locator(".pf-row__action").first().click().catch(() => {});
await page.waitForSelector(".pf-player", { timeout: 5000 });
await page.selectOption(".pf-player__rate select", "1.5");
await page.waitForTimeout(400);

const read = () =>
  page.evaluate(() => ({
    stored: localStorage.getItem("pf-rate"),
    audio: document.querySelector("audio")?.playbackRate ?? null,
    select: document.querySelector(".pf-player__rate select")?.value ?? null,
  }));

console.log("after choosing ", await read());
await page.reload({ waitUntil: "networkidle" });
await page.waitForTimeout(600);
console.log("after reload   ", await read());

// The real proof: play something on the fresh page and see the control agree.
await page.click(".pf-tabset__tab:nth-child(2)").catch(() => {});
await page.locator(".pf-row__action").first().click().catch(() => {});
await page.waitForSelector(".pf-player", { timeout: 5000 });
await page.waitForTimeout(500);
console.log("playing again  ", await read());

await browser.close();
await tearDown();
