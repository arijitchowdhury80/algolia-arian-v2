import assert from "node:assert/strict";
import { readdir, readFile } from "node:fs/promises";
import test from "node:test";

const repoRoot = new URL("../", import.meta.url);
const reportsRoot = new URL("../reports/", import.meta.url);

const auditSlugs = [
  "british-airways",
  "brooks-running",
  "dell",
  "dsw",
  "footlocker",
  "homedepot-mexico",
  "jbl",
  "labanquepostale",
  "llbean",
  "michaelkors",
  "nike",
  "oriental-trading",
  "orientaltrading",
  "petsmart",
  "savage-x-fenty",
  "thenorthface",
  "torrid",
];

const indexedAuditSlugs = [
  "british-airways",
  "brooks-running",
  "dsw",
  "llbean",
  "labanquepostale",
  "nike",
  "oriental-trading",
  "petsmart",
  "savage-x-fenty",
  "homedepot-mexico",
];

test("audit directories live under the reports IA root", async () => {
  const rootEntries = await readdir(repoRoot, { withFileTypes: true });
  const reportsEntries = await readdir(reportsRoot, { withFileTypes: true });
  const rootDirs = new Set(rootEntries.filter((entry) => entry.isDirectory()).map((entry) => entry.name));
  const reportDirs = new Set(reportsEntries.filter((entry) => entry.isDirectory()).map((entry) => entry.name));

  for (const slug of auditSlugs) {
    assert.equal(rootDirs.has(slug), false, `Expected /${slug} to move under /reports/${slug}`);
    assert.equal(reportDirs.has(slug), true, `Expected /reports/${slug} to exist`);
  }
});

test("audit data snapshots live under reports/data, not the repository root", async () => {
  const rootEntries = await readdir(repoRoot, { withFileTypes: true });
  const dataEntries = await readdir(new URL("../reports/data/", import.meta.url), { withFileTypes: true });
  const rootFiles = new Set(rootEntries.filter((entry) => entry.isFile()).map((entry) => entry.name));
  const dataFiles = new Set(dataEntries.filter((entry) => entry.isFile()).map((entry) => entry.name));

  for (const slug of indexedAuditSlugs) {
    const file = `${slug}-audit-data.json`;
    assert.equal(rootFiles.has(file), false, `Expected /${file} to move under /reports/data/${file}`);
    assert.equal(dataFiles.has(file), true, `Expected /reports/data/${file} to exist`);
  }
});

test("reports index routes every audit card through /reports", async () => {
  const html = await readFile(new URL("../reports/index.html", import.meta.url), "utf8");

  for (const slug of indexedAuditSlugs) {
    assert.match(html, new RegExp(`href="/reports/${slug}/"`));
    assert.doesNotMatch(html, new RegExp(`href="/${slug}/"`));
  }
});

test("publish script writes generated reports back into the reports tree", async () => {
  const publishScript = await readFile(new URL("../publish.sh", import.meta.url), "utf8");

  assert.match(publishScript, /REPORTS_DIR="\$REPO_DIR\/reports"/);
  assert.match(publishScript, /DATA_DIR="\$REPORTS_DIR\/data"/);
  assert.match(publishScript, /"\$REPORTS_DIR\/\$SLUG\/index\.html"/);
  assert.match(publishScript, /"\$DATA_DIR\/\$SLUG-audit-data\.json"/);
  assert.doesNotMatch(publishScript, /"\$REPO_DIR\/\$SLUG-audit-data\.json"/);
});

test("README documents reports as the owner of audit pages and data", async () => {
  const readme = await readFile(new URL("../README.md", import.meta.url), "utf8");

  assert.match(readme, /reports\/\{account\}\//);
  assert.match(readme, /reports\/data\/\*-audit-data\.json/);
  assert.doesNotMatch(readme, /├── \{account\}\//);
  assert.doesNotMatch(readme, /├── \*-audit-data\.json/);
});
