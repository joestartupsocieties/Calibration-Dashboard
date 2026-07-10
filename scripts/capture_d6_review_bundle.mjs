import { spawn } from "node:child_process";
import fs from "node:fs/promises";
import path from "node:path";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || "playwright");

const root = process.cwd();
const python = process.env.PYTHON_EXE || "python";
const port = Number(process.env.STREAMLIT_CAPTURE_PORT || 8540);
const baseUrl = `http://127.0.0.1:${port}`;
const screenshotDir = path.join(root, "review_bundle_d6_mvp", "screenshots");
const logDir = path.join(root, "review_bundle_d6_mvp", "logs");

await fs.mkdir(screenshotDir, { recursive: true });
await fs.mkdir(logDir, { recursive: true });

const server = spawn(
  python,
  ["-m", "streamlit", "run", "app.py", "--server.port", String(port), "--server.headless", "true", "--browser.gatherUsageStats", "false"],
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

try {
  await waitForServer(baseUrl, 45_000);
  const browser = await chromium.launch({
    headless: true,
    executablePath: process.env.CHROME_EXECUTABLE || undefined,
  });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  const qaRows = [];

  await page.goto(baseUrl, { waitUntil: "networkidle" });
  await stableRender(page);
  await assertPage(page, "Calibration Analysis", ["SEZ Incentive Transition Triage", "Synthetic demo view", "Gate-cleared enterprise records"]);
  await page.screenshot({ path: path.join(screenshotDir, "01_calibration_analysis_default.png"), fullPage: true });
  qaRows.push("01_calibration_analysis_default.png - title, metric cards, scenario comparison, annual results.");

  await openExpander(page, "Model assumptions and scenario definitions");
  await stableRender(page);
  await assertPage(page, "Calibration Analysis", ["Core assumptions", "Sensitivity outputs"]);
  await page.screenshot({ path: path.join(screenshotDir, "02_calibration_analysis_assumptions_sensitivity.png"), fullPage: true });
  qaRows.push("02_calibration_analysis_assumptions_sensitivity.png - assumptions and sensitivity expander.");

  await clickNav(page, "Readiness Triage");
  await assertPage(page, "Readiness Triage", ["Pathway summary", "Provisional review pathway"]);
  await page.screenshot({ path: path.join(screenshotDir, "03_readiness_triage.png"), fullPage: true });
  qaRows.push("03_readiness_triage.png - readiness pathways and triage table.");

  await clickNav(page, "Case Calibration");
  await assertPage(page, "Case Calibration", ["D6 calibration support inputs", "Reason codes"]);
  await page.screenshot({ path: path.join(screenshotDir, "04_case_calibration_gate_cleared_or_default.png"), fullPage: true });
  qaRows.push("04_case_calibration_gate_cleared_or_default.png - selected case calibration memo and D6 inputs.");

  await clickNav(page, "Evidence & Exports");
  await assertPage(page, "Evidence & Exports", ["Source-data confidence", "Export package"]);
  await page.screenshot({ path: path.join(screenshotDir, "05a_evidence_source_confidence.png"), fullPage: true });
  qaRows.push("05a_evidence_source_confidence.png - source-data confidence tab.");
  await page.getByText("Calibration evidence", { exact: true }).click();
  await stableRender(page);
  await assertPage(page, "Evidence & Exports", ["Model readiness", "Enterprise-to-zone reconciliation"]);
  await page.screenshot({ path: path.join(screenshotDir, "05b_evidence_calibration_checks.png"), fullPage: true });
  qaRows.push("05b_evidence_calibration_checks.png - model readiness, reconciliation, blocked records, verification rules.");
  await page.getByText("Export package", { exact: true }).click();
  await stableRender(page);
  await assertPage(page, "Evidence & Exports", ["Full Excel Workbook", "Pathway Rationale CSV"]);
  await page.screenshot({ path: path.join(screenshotDir, "05c_evidence_export_package.png"), fullPage: true });
  qaRows.push("05c_evidence_export_package.png - workbook and supporting CSV downloads.");

  await clickNav(page, "About / Limitations");
  await assertPage(page, "About / Limitations", ["Public demo posture", "No pilot zone is selected"]);
  await page.screenshot({ path: path.join(screenshotDir, "06_about_limitations.png"), fullPage: true });
  qaRows.push("06_about_limitations.png - public-demo posture and limitations.");

  await browser.close();
  await fs.writeFile(path.join(logDir, "visual_qa_summary.md"), `# Visual QA Summary\n\n${qaRows.map((row) => `- ${row}`).join("\n")}\n`, "utf8");
} finally {
  server.kill();
  await fs.writeFile(path.join(logDir, "streamlit_stdout.log"), stdout.join(""), "utf8");
  await fs.writeFile(path.join(logDir, "streamlit_stderr.log"), stderr.join(""), "utf8");
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
    await new Promise((resolve) => setTimeout(resolve, 750));
  }
  throw new Error(`Timed out waiting for ${url}`);
}

async function stableRender(page) {
  await page.waitForLoadState("networkidle");
  await page.waitForTimeout(1250);
}

async function clickNav(page, label) {
  await page.getByText(label, { exact: true }).click();
  await stableRender(page);
}

async function openExpander(page, label) {
  const target = page.getByText(label, { exact: true });
  await target.click();
  await stableRender(page);
}

async function assertPage(page, heading, requiredText) {
  const body = await page.locator("body").innerText();
  const bodyLower = body.toLowerCase();
  const missing = [heading, ...requiredText].filter((text) => !bodyLower.includes(text.toLowerCase()));
  if (missing.length) {
    throw new Error(`Missing expected rendered text on ${heading}: ${missing.join(", ")}`);
  }
  if (body.includes("Traceback") || body.includes("Uncaught app exception")) {
    throw new Error(`Traceback or app exception visible on ${heading}`);
  }
}
