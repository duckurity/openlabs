const { chromium } = require("playwright");

const BASE_URL = process.env.CHALLENGE_URL || "http://127.0.0.1:5000/";
const ADMIN_BOT_TOKEN = process.env.ADMIN_BOT_TOKEN || "local-admin-bot";
const MIN_INTERVAL = Number.parseInt(process.env.BOT_INTERVAL_MIN || "10", 10);
const MAX_INTERVAL = Number.parseInt(process.env.BOT_INTERVAL_MAX || "20", 10);

function randomDelay() {
  const min = Math.min(MIN_INTERVAL, MAX_INTERVAL);
  const max = Math.max(MIN_INTERVAL, MAX_INTERVAL);
  return Math.floor(Math.random() * (max - min + 1) + min) * 1000;
}

async function reviewOnce() {
  const browser = await chromium.launch({
    headless: true,
    args: ["--no-sandbox"],
  });
  try {
    const context = await browser.newContext({
      extraHTTPHeaders: { "X-Admin-Bot-Token": ADMIN_BOT_TOKEN },
    });
    const page = await context.newPage();
    const dashboardUrl = new URL("/admin/dashboard", BASE_URL).toString();
    await page.goto(dashboardUrl, { waitUntil: "networkidle" });
    await page.waitForTimeout(1000);
  } finally {
    await browser.close();
  }
}

async function main() {
  const once = process.env.BOT_ONCE === "1";
  while (true) {
    try {
      await reviewOnce();
      console.log("Admin review completed");
    } catch (error) {
      console.error("Admin review failed:", error.message);
      if (once) process.exitCode = 1;
    }

    if (once) return;
    await new Promise((resolve) => setTimeout(resolve, randomDelay()));
  }
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
