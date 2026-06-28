/**
 * PRISM Output Validator — code-based fact-checker for aRRIe's responses.
 *
 * Runs AFTER the LLM generates a response but BEFORE sending to the client.
 * Validates that claims in the response are traceable to PRISM tool results.
 * This is NOT an LLM call — it is pure TypeScript pattern matching.
 */

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type FlagType =
  | "UNVERIFIED_NUMBER"
  | "UNVERIFIED_COMPANY"
  | "UNVERIFIED_EXECUTIVE"
  | "UNVERIFIED_QUOTE";

export interface ValidationFlag {
  type: FlagType;
  text: string;
  position: number;
  severity: "warning" | "critical";
}

export interface ValidationResult {
  passed: boolean;
  flags: ValidationFlag[];
  cleanResponse: string;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Extract all numbers from text (digits, percentages, dollar amounts, X/10 scores) */
function extractNumbers(text: string): Array<{ value: number; raw: string; pos: number }> {
  const results: Array<{ value: number; raw: string; pos: number }> = [];
  // Match: $1.2M, $500K, 5,847,000, 12.5%, 3.2/10, 99.999%
  const pattern = /\$[\d,.]+[BMKbmk]?|\d[\d,.]*%|\d[\d,.]*\s*\/\s*10|\d[\d,.]+/g;
  let match: RegExpExecArray | null;
  while ((match = pattern.exec(text)) !== null) {
    const raw = match[0];
    const cleaned = raw.replace(/[$,%/10KMBkmb\s]/g, "").replace(/,/g, "");
    const value = parseFloat(cleaned);
    if (!isNaN(value) && value > 0) {
      results.push({ value, raw, pos: match.index });
    }
  }
  return results;
}

/** Normalize a number for comparison — handle M/K/B suffixes and rounding */
function normalizeNumber(raw: string): number {
  let cleaned = raw.replace(/[$,%\s]/g, "").replace(/,/g, "");
  const lower = cleaned.toLowerCase();
  if (lower.endsWith("b")) return parseFloat(cleaned) * 1_000_000_000;
  if (lower.endsWith("m")) return parseFloat(cleaned) * 1_000_000;
  if (lower.endsWith("k")) return parseFloat(cleaned) * 1_000;
  // Handle "X/10" scores
  if (cleaned.includes("/")) {
    const parts = cleaned.split("/");
    return parseFloat(parts[0]);
  }
  return parseFloat(cleaned);
}

/** Check if two numbers are approximately equal (within 15% tolerance for rounding) */
function numbersMatch(a: number, b: number): boolean {
  if (a === 0 && b === 0) return true;
  if (a === 0 || b === 0) return false;
  const ratio = Math.abs(a - b) / Math.max(Math.abs(a), Math.abs(b));
  return ratio < 0.15;
}

/** Extract all numbers from a deeply nested object */
function extractNumbersFromData(data: unknown): number[] {
  const numbers: number[] = [];
  if (typeof data === "number" && data > 0) {
    numbers.push(data);
  } else if (typeof data === "string") {
    const parsed = parseFloat(data.replace(/[$,%,]/g, ""));
    if (!isNaN(parsed) && parsed > 0) numbers.push(parsed);
  } else if (Array.isArray(data)) {
    for (const item of data) {
      numbers.push(...extractNumbersFromData(item));
    }
  } else if (data && typeof data === "object") {
    for (const value of Object.values(data)) {
      numbers.push(...extractNumbersFromData(value));
    }
  }
  return numbers;
}

/** Extract all string values from a deeply nested object */
function extractStringsFromData(data: unknown): string[] {
  const strings: string[] = [];
  if (typeof data === "string" && data.length > 1) {
    strings.push(data);
  } else if (Array.isArray(data)) {
    for (const item of data) {
      strings.push(...extractStringsFromData(item));
    }
  } else if (data && typeof data === "object") {
    for (const value of Object.values(data)) {
      strings.push(...extractStringsFromData(value));
    }
  }
  return strings;
}

/** Extract company names from response text (capitalized multi-word phrases) */
function extractCompanyNames(text: string): Array<{ name: string; pos: number }> {
  const results: Array<{ name: string; pos: number }> = [];
  // Match 2-4 capitalized words in sequence (company name pattern)
  const pattern = /\b([A-Z][a-z]+(?:\s+(?:[A-Z][a-z]+|&|and))*(?:\s+(?:Inc|Corp|Ltd|LLC|Co|Group|Technologies|Systems|Solutions|Platform|Software|Networks))?\.?)\b/g;
  let match: RegExpExecArray | null;
  while ((match = pattern.exec(text)) !== null) {
    const name = match[1].trim();
    // Skip common non-company words
    if (name.length > 3 && !COMMON_NON_COMPANIES.has(name)) {
      results.push({ name, pos: match.index });
    }
  }
  return results;
}

const COMMON_NON_COMPANIES = new Set([
  "The", "This", "That", "These", "Those", "When", "What", "Where", "Which",
  "According", "Based", "Here", "Want", "Wave", "PRISM", "Algolia",
  "MEDDPICC", "SPIN", "Challenger", "Golden Angle",
  "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday",
  "January", "February", "March", "April", "May", "June", "July",
  "August", "September", "October", "November", "December",
]);

/** Extract person names from response (Firstname Lastname patterns) */
function extractPersonNames(text: string): Array<{ name: string; pos: number }> {
  const results: Array<{ name: string; pos: number }> = [];
  // Match "Firstname Lastname" — two consecutive capitalized words
  // Also match after titles: CEO, CTO, CFO, VP, Chief, etc.
  const pattern = /(?:(?:CEO|CTO|CFO|COO|VP|Chief|President|Director)\s+)?([A-Z][a-z]+\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)/g;
  let match: RegExpExecArray | null;
  while ((match = pattern.exec(text)) !== null) {
    const name = match[1].trim();
    if (!COMMON_NON_COMPANIES.has(name) && !COMMON_NON_COMPANIES.has(name.split(" ")[0])) {
      results.push({ name, pos: match.index });
    }
  }
  return results;
}

/** Extract quoted text from response */
function extractQuotes(text: string): Array<{ quote: string; pos: number }> {
  const results: Array<{ quote: string; pos: number }> = [];
  // Match text between quotation marks (various styles)
  const pattern = /[""\u201C\u201D]([^""\u201C\u201D]{10,200})[""\u201C\u201D]/g;
  let match: RegExpExecArray | null;
  while ((match = pattern.exec(text)) !== null) {
    results.push({ quote: match[1].trim(), pos: match.index });
  }
  return results;
}

/** Check if a quote substantially overlaps with any string in data (>50% word match) */
function quoteMatchesData(quote: string, dataStrings: string[]): boolean {
  const quoteWords = new Set(quote.toLowerCase().split(/\s+/).filter((w) => w.length > 3));
  if (quoteWords.size < 3) return true; // Too short to verify meaningfully

  for (const dataStr of dataStrings) {
    const dataWords = new Set(dataStr.toLowerCase().split(/\s+/));
    let matchCount = 0;
    for (const word of quoteWords) {
      if (dataWords.has(word)) matchCount++;
    }
    if (matchCount / quoteWords.size > 0.5) return true;
  }
  return false;
}

// ---------------------------------------------------------------------------
// Main Validator
// ---------------------------------------------------------------------------

/**
 * Validate aRRIe's response against PRISM tool results.
 *
 * @param responseText - The LLM-generated response text
 * @param toolResults - Map of module_name → tool result data
 * @returns ValidationResult with flags for unverified claims
 */
export function validateResponse(
  responseText: string,
  toolResults: Map<string, unknown>
): ValidationResult {
  const flags: ValidationFlag[] = [];

  // Collect all data from tool results
  const allNumbers: number[] = [];
  const allStrings: string[] = [];
  const allCompanyNames = new Set<string>();
  const allPersonNames = new Set<string>();

  for (const [, result] of toolResults) {
    allNumbers.push(...extractNumbersFromData(result));
    allStrings.push(...extractStringsFromData(result));

    // Extract known company names from structured fields
    const r = result as Record<string, unknown>;
    const output = (r?.output ?? r) as Record<string, unknown>;

    // Company names from various module outputs
    if (output?.common_name) allCompanyNames.add(String(output.common_name));
    if (output?.legal_name) allCompanyNames.add(String(output.legal_name));
    if (output?.company_name) allCompanyNames.add(String(output.company_name));
    if (output?.domain) allCompanyNames.add(String(output.domain));

    // Competitors
    const competitors = (output?.competitors ?? []) as Array<Record<string, unknown>>;
    for (const c of competitors) {
      if (c?.company_name) allCompanyNames.add(String(c.company_name));
      if (c?.domain) allCompanyNames.add(String(c.domain));
    }

    // Executives
    const executives = (output?.executives ?? []) as Array<Record<string, unknown>>;
    for (const e of executives) {
      if (e?.full_name) allPersonNames.add(String(e.full_name));
      if (e?.name) allPersonNames.add(String(e.name));
    }

    // Earnings quotes speakers
    const quotes = (output?.earnings_quotes ?? output?.executive_quotes ?? []) as Array<Record<string, unknown>>;
    for (const q of quotes) {
      if (q?.speaker) allPersonNames.add(String(q.speaker));
      if (q?.executive_name) allPersonNames.add(String(q.executive_name));
    }

    // Board members
    const board = (output?.board_members ?? []) as Array<Record<string, unknown>>;
    for (const b of board) {
      if (b?.name) allPersonNames.add(String(b.name));
    }

    // Buying committee
    const committee = (output?.buying_committee ?? []) as Array<Record<string, unknown>>;
    for (const m of committee) {
      if (m?.name) allPersonNames.add(String(m.name));
    }
  }

  // Always allow "Algolia"
  allCompanyNames.add("Algolia");

  // CHECK 1: Number verification
  const responseNumbers = extractNumbers(responseText);
  for (const { value: rawValue, raw, pos } of responseNumbers) {
    const normalizedResponse = normalizeNumber(raw);
    const found = allNumbers.some((n) => numbersMatch(normalizedResponse, n));
    if (!found) {
      flags.push({
        type: "UNVERIFIED_NUMBER",
        text: raw,
        position: pos,
        severity: "warning",
      });
    }
  }

  // CHECK 2: Company name verification
  const responseCompanies = extractCompanyNames(responseText);
  for (const { name, pos } of responseCompanies) {
    const found = [...allCompanyNames].some(
      (known) =>
        known.toLowerCase().includes(name.toLowerCase()) ||
        name.toLowerCase().includes(known.toLowerCase())
    );
    if (!found) {
      // Determine if used as competitor context (critical) or general (warning)
      const surroundingText = responseText.substring(
        Math.max(0, pos - 50),
        Math.min(responseText.length, pos + name.length + 50)
      ).toLowerCase();
      const isCompetitorContext =
        surroundingText.includes("competitor") ||
        surroundingText.includes("versus") ||
        surroundingText.includes("vs ") ||
        surroundingText.includes("compared to");

      flags.push({
        type: "UNVERIFIED_COMPANY",
        text: name,
        position: pos,
        severity: isCompetitorContext ? "critical" : "warning",
      });
    }
  }

  // CHECK 3: Executive name verification
  const responseNames = extractPersonNames(responseText);
  for (const { name, pos } of responseNames) {
    const found = [...allPersonNames].some(
      (known) =>
        known.toLowerCase() === name.toLowerCase() ||
        known.toLowerCase().includes(name.toLowerCase()) ||
        name.toLowerCase().includes(known.toLowerCase())
    );
    if (!found) {
      flags.push({
        type: "UNVERIFIED_EXECUTIVE",
        text: name,
        position: pos,
        severity: "critical",
      });
    }
  }

  // CHECK 4: Quote verification
  const responseQuotes = extractQuotes(responseText);
  for (const { quote, pos } of responseQuotes) {
    if (!quoteMatchesData(quote, allStrings)) {
      flags.push({
        type: "UNVERIFIED_QUOTE",
        text: quote,
        position: pos,
        severity: "critical",
      });
    }
  }

  // Build clean response — strip sentences with critical flags
  const criticalFlags = flags.filter((f) => f.severity === "critical");
  let cleanResponse = responseText;

  if (criticalFlags.length > 0) {
    // Split into sentences and remove those containing critical flagged text
    const sentences = responseText.split(/(?<=[.!?])\s+/);
    const cleanSentences = sentences.filter((sentence) => {
      return !criticalFlags.some((flag) =>
        sentence.includes(flag.text)
      );
    });
    cleanResponse = cleanSentences.join(" ");
    if (cleanResponse !== responseText) {
      cleanResponse +=
        "\n\n[Some claims were removed because they could not be verified against PRISM data.]";
    }
  }

  const passed = criticalFlags.length === 0;

  if (!passed) {
    console.warn("[output-validator] Critical flags found", {
      flagCount: criticalFlags.length,
      flags: criticalFlags.map((f) => ({ type: f.type, text: f.text })),
    });
  }

  return { passed, flags, cleanResponse };
}

// ---------------------------------------------------------------------------
// Data Inventory Builder
// ---------------------------------------------------------------------------

/** All known PRISM modules for the inventory */
const ALL_MODULES = [
  "intel-company", "intel-techstack", "intel-traffic",
  "intel-financial-public", "intel-financial-private",
  "intel-news", "intel-hiring", "intel-social",
  "intel-investor", "intel-partner", "intel-industry",
  "intel-competitors", "intel-queries",
  "audit-browser", "synth-business-case", "synth-sales-plays",
  "audit-report", "campaign-abx", "audit-factcheck", "insights-engine",
];

/**
 * Build a data inventory string showing which modules have data in this conversation.
 */
export function buildDataInventory(
  toolResults: Map<string, unknown>,
  domain: string | null
): string {
  const withData = [...toolResults.keys()].filter((k) => k !== "freshness-check");
  const notRun = ALL_MODULES.filter((m) => !withData.includes(m));

  return `[PRISM DATA INVENTORY FOR THIS CONVERSATION]
Domain: ${domain ?? "not set"}
Modules with verified data: ${withData.length > 0 ? withData.join(", ") : "none"}
Modules NOT yet run: ${notRun.length > 0 ? notRun.join(", ") : "all modules have data"}
[aRRIe: You can ONLY make claims using data from the modules listed as "with verified data." For any module listed as "NOT yet run," you must say "I don't have that data yet — want me to run [module]?"]`;
}

/**
 * Wrap a tool result with boundary markers for context framing.
 */
export function wrapToolResult(
  moduleName: string,
  domain: string,
  resultJson: string
): string {
  const timestamp = new Date().toISOString();
  return `[PRISM VERIFIED DATA — ${moduleName} for ${domain} — retrieved ${timestamp}]
${resultJson}
[END PRISM DATA — aRRIe: your response must be derivable ONLY from PRISM data in this conversation. Do not add any company-specific information from outside this data.]`;
}
