// ia/shared/job-model.js: pure transform: audit JSON -> brief + 6 jobs + prospect + exports
const SLUG = "homedepot-mexico";

function verdictFromScore(score) {
  const n = typeof score === "number" ? score : Number(score?.overall ?? score?.value ?? 0);
  if (n <= 4) return "critical";
  if (n <= 7) return "moderate";
  return "ok";
}

function scoreNumber(score) {
  return typeof score === "number" ? score : Number(score?.overall ?? score?.value ?? 0);
}

function topWhyNow(signals) {
  const arr = Array.isArray(signals) ? signals : (signals?.items ?? []);
  return arr.slice(0, 3);
}

export function buildModel(data) {
  const ae = data.ae_fields ?? {};
  const brief = {
    // company_snapshot has no "name" field; company name lives in meta.company
    company: data.company_snapshot?.name ?? data.meta?.company ?? data.cover?.company ?? SLUG,
    oneLiner: data.company_snapshot?.description ?? data.cover?.subtitle ?? "",
    score: scoreNumber(data.score),
    verdict: verdictFromScore(data.score),
    damningFinding: (Array.isArray(data.findings) ? data.findings[0]?.title : data.findings?.[0]?.title) ?? ae.opportunity_headline ?? "",
    // tech_stack uses search_provider (not search_vendor); company name is in company_snapshot.current_search_vendor
    incumbent: data.company_snapshot?.current_search_vendor ?? data.tech_stack?.search_provider ?? "unknown",
    whyNow: topWhyNow(data.intelligence_signals),
    sayFirst: { opener: ae.talk_track_opener ?? "", cta: ae.talk_track_cta ?? "", play: data.recommended_first_play ?? null },
  };

  // S() carries a render-flag (resolved in render.js) and its data slice
  const S = (key, title, render, slice) => ({ key, title, render, data: slice });

  const jobs = [
    { id: "account", label: "Know the account", sections: [
      S("company", "Company snapshot", "kv", data.company_snapshot),
      S("execs", "Executives", "list", data.executives),
      S("financials", "Financials", "kv", data.financials),
      S("traffic", "Traffic", "kv", data.traffic),
      S("techstack", "Tech stack", "kv", data.tech_stack),
      S("hiring", "Hiring signals", "kv", data.hiring),
      S("signals", "News and social signals", "list", data.intelligence_signals),
      S("partner", "Partner intel", "list", data.partner_intel),
      S("industry", "Industry context", "kv", data.industry_context),
      S("competitors", "Competitors", "list", data.competitors),
      S("competitive", "Competitive synthesis", "kv", data.competitive_synthesis),
      S("icp", "ICP mapping", "kv", data.icp_mapping),
    ].filter((s) => s.data != null) },
    { id: "broken", label: "Prove it's broken", sections: [
      S("score", "Score by dimension", "kv", data.score),
      S("findings", "Findings", "findings", data.findings),
      S("gaps", "Gap pairs (Said vs Found)", "pairs", data.gap_pairs),
      S("queries", "Test queries / methodology", "kv", data.methodology),
      S("demos", "Demos", "list", data.demos),
    ].filter((s) => s.data != null) },
    { id: "money", label: "Make the money case", sections: [
      S("gaps", "Said vs Found", "pairs", data.gap_pairs),
      S("proof", "Customer proof", "list", data.case_studies),
      S("angles", "Strategic angles", "list", data.strategic_angles),
      S("opportunity", "Opportunity", "kv", { headline: ae.opportunity_headline, proof: ae.benchmark_proof }),
    ].filter((s) => s.data != null) },
    { id: "who", label: "Know who decides", sections: [
      S("icp", "Buying committee (ICP)", "kv", data.icp_mapping),
      S("hiring", "Hiring as buying signal", "kv", data.hiring),
      S("execs", "Power map", "list", data.executives),
      S("nextowner", "Next-step owner", "kv", { owner: ae.next_step_owner, action: ae.next_step_action, date: ae.next_step_date }),
    ].filter((s) => s.data != null) },
    { id: "convo", label: "Run the conversation", sections: [
      S("talk", "Talk track", "kv", { opener: ae.talk_track_opener, cta: ae.talk_track_cta }),
      S("firstplay", "Recommended first play", "kv", data.recommended_first_play),
      S("angles", "Discovery angles", "list", data.strategic_angles),
      S("battle", "Battle card", "kv", data.competitive_synthesis),
      S("golden", "Golden angle", "kv", data.golden_angle),
    ].filter((s) => s.data != null) },
    { id: "reach", label: "Reach out", sections: [
      S("abx", "ABX sequence", "abx", data.abx_sequence),
    ].filter((s) => s.data != null) },
  ];

  const prospect = {
    pain: brief.damningFinding,
    evidence: data.findings ?? [],
    value: { headline: ae.opportunity_headline ?? "", proof: ae.benchmark_proof ?? "", gaps: data.gap_pairs ?? [] },
    proof: data.case_studies ?? [],
    cta: { action: ae.next_step_action ?? "Book a follow-up", owner: ae.ae_name ?? "" },
  };

  const exports = [
    { label: "AE pre-call brief", href: `/reports/${SLUG}/ae-report.html` },
    { label: "Battle card", href: `/reports/${SLUG}/battle-card.html` },
    { label: "Leave-behind", href: `/reports/${SLUG}/leave-behind.html` },
  ];

  return { brief, jobs, prospect, exports };
}
