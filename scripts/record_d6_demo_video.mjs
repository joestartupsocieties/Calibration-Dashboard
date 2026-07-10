import { spawn } from "node:child_process";
import fs from "node:fs/promises";
import path from "node:path";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || "playwright");

const root = process.cwd();
const python = process.env.PYTHON_EXE || "python";
const port = Number(process.env.STREAMLIT_DEMO_PORT || 8541);
const baseUrl = `http://127.0.0.1:${port}`;
const bundleDir = path.join(root, "review_bundle_d6_mvp");
const videoDir = path.join(bundleDir, "demo_video");
const rawVideoDir = path.join(videoDir, "raw");
const logDir = path.join(bundleDir, "logs");
const finalVideo = path.join(videoDir, "sez_d6_calibration_mvp_demo.webm");

await fs.mkdir(rawVideoDir, { recursive: true });
await fs.mkdir(logDir, { recursive: true });

const server = spawn(
  python,
  [
    "-m",
    "streamlit",
    "run",
    "app.py",
    "--server.port",
    String(port),
    "--server.headless",
    "true",
    "--browser.gatherUsageStats",
    "false",
  ],
  {
    cwd: root,
    env: { ...process.env, PYTHONUNBUFFERED: "1" },
    stdio: ["ignore", "pipe", "pipe"],
  },
);

const stdout = [];
const stderr = [];
server.stdout.on("data", (chunk) => stdout.push(chunk.toString()));
server.stderr.on("data", (chunk) => stderr.push(chunk.toString()));

const actions = [];

try {
  await waitForServer(baseUrl, 45_000);
  const browser = await chromium.launch({
    headless: true,
    executablePath: process.env.CHROME_EXECUTABLE || undefined,
  });
  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    recordVideo: { dir: rawVideoDir, size: { width: 1440, height: 900 } },
  });
  const page = await context.newPage();

  await page.goto(baseUrl, { waitUntil: "networkidle" });
  await stableRender(page);
  await assertNoVisibleFailure(page, "Calibration Analysis");
  actions.push("Opened Calibration Analysis default landing view.");
  await pause(1500);
  await scrollThrough(page, 4);
  await clickIfPresent(page, "Model assumptions and scenario definitions");
  actions.push("Opened model assumptions and sensitivity information.");
  await scrollThrough(page, 3);

  await clickNav(page, "Readiness Triage");
  actions.push("Opened Readiness Triage and reviewed pathway table.");
  await scrollThrough(page, 5);

  await clickNav(page, "Case Calibration");
  actions.push("Opened Case Calibration and reviewed selected-zone memo, gates, reasons, and D6 inputs.");
  await scrollThrough(page, 6);

  await clickNav(page, "Evidence & Exports");
  actions.push("Opened Evidence & Exports.");
  await scrollThrough(page, 3);
  await clickIfPresent(page, "Calibration evidence");
  actions.push("Opened Calibration evidence tab.");
  await scrollThrough(page, 5);
  await clickIfPresent(page, "Export package");
  actions.push("Opened Export package tab and showed downloadable work products.");
  await scrollThrough(page, 4);

  await clickNav(page, "About / Limitations");
  actions.push("Opened About / Limitations and reviewed public-demo posture.");
  await scrollThrough(page, 4);

  await context.close();
  await browser.close();

  const recordedPath = await page.video().path();
  await replaceFile(recordedPath, finalVideo);
  await fs.writeFile(
    path.join(logDir, "demo_video_summary.md"),
    `# Demo Video Summary\n\n- Video: ${finalVideo}\n- Viewport: 1440x900\n- Local URL: ${baseUrl}\n\n## Recorded actions\n\n${actions
      .map((action) => `- ${action}`)
      .join("\n")}\n`,
    "utf8",
  );
} finally {
  server.kill();
  await fs.writeFile(path.join(logDir, "video_streamlit_stdout.log"), stdout.join(""), "utf8");
  await fs.writeFile(path.join(logDir, "video_streamlit_stderr.log"), stderr.join(""), "utf8");
}

async function waitForServer(url, timeoutMs) {
  const started = Date.now();
  while (Date.now() - started < timeoutMs) {
    try {
      const response = await fetch(url);
      if (response.ok) return;
    } catch {
      // Retry until timeout.
    }
    await pause(750);
  }
  throw new Error(`Timed out waiting for ${url}`);
}

async function stableRender(page) {
  await page.waitForLoadState("networkidle");
  await page.waitForTimeout(1250);
}

async function clickNav(page, label) {
  await page.getByText(label, { exact: true }).first().click();
  await stableRender(page);
  await assertNoVisibleFailure(page, label);
}

async function clickIfPresent(page, label) {
  const target = page.getByText(label, { exact: true }).first();
  if ((await target.count()) === 0) return false;
  await target.click();
  await stableRender(page);
  return true;
}

async function scrollThrough(page, steps) {
  for (let step = 0; step < steps; step += 1) {
    await page.mouse.wheel(0, 620);
    await pause(850);
  }
  await page.keyboard.press("Home");
  await pause(900);
}

async function assertNoVisibleFailure(page, label) {
  const body = await page.locator("body").innerText();
  if (body.includes("Traceback") || body.includes("Uncaught app exception")) {
    throw new Error(`Traceback or app exception visible on ${label}`);
  }
}

async function replaceFile(source, target) {
  await fs.rm(target, { force: true });
  await fs.copyFile(source, target);
}

function pause(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
