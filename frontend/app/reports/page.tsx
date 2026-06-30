import { readdir } from "node:fs/promises";
import path from "node:path";
import Link from "next/link";

const REPORTS_DIR = process.env.REPORTS_HTML_DIR ?? path.join(process.cwd(), "report-data");

export default async function ReportsPage() {
  let slugs: string[] = [];
  try {
    const entries = await readdir(REPORTS_DIR, { withFileTypes: true });
    slugs = entries.filter((e) => e.isDirectory()).map((e) => e.name).sort();
  } catch {
    slugs = [];
  }
  return (
    <main style={{ maxWidth: 720, margin: "4rem auto", padding: "0 1rem" }}>
      <h1>Audit reports</h1>
      <ul>
        {slugs.map((s) => (
          <li key={s}>
            <Link href={`/reports/${s}/`}>{s}</Link>
          </li>
        ))}
      </ul>
    </main>
  );
}
