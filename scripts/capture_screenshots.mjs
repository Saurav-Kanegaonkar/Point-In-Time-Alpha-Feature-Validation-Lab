import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const { chromium } = require("/Users/sauravkanegaonkar/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright");

const shots = [
  ["Research Cockpit", "docs/images/research-cockpit.png"],
  ["Validation Suite", "docs/images/validation-suite.png"],
  ["Feed Monitor", "docs/images/feed-monitor.png"],
  ["Research Memo", "docs/images/research-memo.png"],
];

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 1040 }, deviceScaleFactor: 1 });
await page.goto("http://127.0.0.1:4173", { waitUntil: "networkidle" });

for (const [label, path] of shots) {
  if (label !== "Research Cockpit") {
    await page.getByRole("button", { name: label }).click();
  }
  await page.screenshot({ path, fullPage: false });
}

await browser.close();
console.log("Captured portfolio artifact screenshots.");
