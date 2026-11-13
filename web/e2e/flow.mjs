import { chromium } from "playwright";

const base = process.env.WORKBENCH_URL ?? "http://127.0.0.1:8765";
const browser = await chromium.launch({ channel: "msedge", headless: true });
const page = await browser.newPage();
const notes = [];
try {
  await page.goto(base, { waitUntil: "networkidle" });
  await page.getByText("DRAFT_NOT_A_PRODUCT_DISPOSITION").waitFor();
  notes.push("notice visible");
  await page.getByRole("button", { name: "Start investigation" }).click();
  await page.getByText("regression", { exact: false }).first().waitFor();
  const body = await page.locator("main").innerText();
  if (!body.includes("SYN-LOG-417-")) {
    throw new Error("citation missing");
  }
  if (body.toLowerCase().includes("marshline")) {
    throw new Error("other tenant leaked into the draft");
  }
  notes.push("draft regression with citation");
  await page.getByRole("button", { name: "compare", exact: true }).click();
  await page.getByRole("button", { name: "Compare", exact: true }).click();
  await page.getByText("SYN-CODE-THERM").waitFor();
  const table = await page.locator("table").innerText();
  if (!table.includes("12")) {
    throw new Error(`compare table missing 12: ${table}`);
  }
  notes.push("compare shows thermal count");
  await page.getByLabel("Fixture token").fill("lab-otto");
  await page.getByRole("button", { name: "review", exact: true }).click();
  await page.getByRole("button", { name: "Load drafts" }).click();
  await page.getByRole("button", { name: "Approve" }).first().click();
  await page.getByText("APPROVED").waitFor();
  notes.push("reviewer approved");
  await page.getByRole("button", { name: "reliability", exact: true }).click();
  await page.getByRole("button", { name: "Load dashboard" }).click();
  await page.getByText("Data-quality failures: 9").waitFor();
  const dash = await page.locator("main").innerText();
  if (!dash.includes("Device calls: 0")) {
    throw new Error("device calls missing");
  }
  notes.push("dashboard dq 9 and device calls 0");
  console.log(notes.join("\n"));
} finally {
  await browser.close();
}
