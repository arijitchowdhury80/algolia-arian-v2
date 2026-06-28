export interface Source {
  field: string;
  value: string;
  tier: "VERIFIED" | "WEBFETCH" | "WEBSEARCH" | "ESTIMATE" | "NO_SOURCE";
  source_url: string | null;
  source_label: string;
  method: string;
  retrieved_at: string;
  confidence: "high" | "medium" | "low";
}

export interface ModuleResult {
  module_name: string;
  module_version: string;
  status: "success" | "partial" | "failed";
  output: Record<string, unknown>;
  sources: Source[];
  duration_ms: number;
  errors: string[];
  warnings: string[];
}

export interface SearchVendor {
  name: string;
  status: "ACTIVE" | "TAG_ONLY" | "REMOVED" | "UNDETECTED";
  detection_source: string;
  evidence_tier: string;
}

export interface TechStackResult {
  search_vendor: SearchVendor | null;
  ecommerce_platform: string | null;
  cms: string | null;
  cdn: string | null;
  analytics: string[];
  personalization: string[];
  bot_detection: string | null;
  all_technologies: Record<string, unknown>[];
  tech_stack_summary: string;
  algolia_detected: boolean;
}

export interface Executive {
  full_name: string;
  title: string;
  linkedin_url: string | null;
  headshot_url: string | null;
  tenure_description: string | null;
  previous_company: string | null;
  previous_role: string | null;
  relevance:
    | "economic_buyer"
    | "technical_evaluator"
    | "champion_candidate"
    | "influencer"
    | "other";
}

export interface Competitor {
  company_name: string;
  domain: string;
  why_competitor: string;
  relative_size: "larger" | "smaller" | "similar" | "unknown";
  is_algolia_customer: boolean;
}

export interface NewsItem {
  headline: string;
  source: string;
  date: string;
  url: string | null;
  category:
    | "leadership_change"
    | "product_launch"
    | "partnership"
    | "financial"
    | "acquisition"
    | "technology"
    | "other";
}

export interface BlogPost {
  title: string;
  date: string;
  url: string | null;
  summary: string;
}

export interface CompanyProfileResult {
  legal_name: string;
  common_name: string;
  domain: string;
  headquarters: string;
  employee_count: number | null;
  employee_count_source: string | null;
  year_founded: number | null;
  business_model: string;
  motto: string | null;
  industry: string;
  sub_vertical: string | null;
  is_public: boolean;
  ticker: string | null;
  parent_company: string | null;
  revenue_estimate: number | null;
  revenue_source: string | null;
  executives: Executive[];
  competitors: Competitor[];
  recent_news: NewsItem[];
  recent_blog_posts: BlogPost[];
  has_search_bar: boolean | null;
  product_categories: string[];
  search_experience_description: string | null;
}

export interface AuditResponse {
  id: string;
  account_id: string;
  domain: string;
  company_name: string;
  status: string;
  score: number | null;
  created_at: string;
}

export interface RunAuditResponse {
  workflow_id: string;
  run_id: string;
  status: string;
}

/* ── Traffic card ── */
export interface TrafficSource {
  direct_pct: number;
  search_pct: number;
  referral_pct: number;
  social_pct: number;
  paid_pct: number;
}

export interface TopCountry {
  country: string;
  pct: number;
}

export interface DeviceSplit {
  desktop: number;
  mobile: number;
  tablet: number;
}

export interface CompetitorTraffic {
  company_name: string;
  domain: string;
  monthly_visits: number;
}

export interface TrafficResult {
  domain: string;
  monthly_visits: number;
  traffic_sources: TrafficSource;
  top_countries: TopCountry[];
  device_split: DeviceSplit;
  bounce_rate: number;
  competitor_traffic: CompetitorTraffic[];
}

/* ── Financial card ── */
export interface RevenueYear {
  year: number;
  revenue: number;
}

export interface FinancialPublicResult {
  ticker: string;
  revenue_3yr: RevenueYear[];
  gross_margin: number;
  operating_margin: number;
  market_cap: number;
  analyst_consensus: string | null;
}

export interface FinancialPrivateResult {
  revenue_estimate_low: number;
  revenue_estimate_high: number;
  revenue_best_estimate: number;
  confidence: "high" | "medium" | "low";
  estimation_sources: string[];
}

/* ── News card ── */
export interface NewsSignalItem {
  headline: string;
  source: string;
  date: string;
  url: string | null;
  category: string;
}

export interface ExecutiveQuote {
  speaker: string;
  quote: string;
  context: string;
  source_url: string | null;
}

export interface UrgencySignal {
  signal_type: string;
  title: string;
  detail: string;
  severity: "HIGH" | "MEDIUM" | "LOW";
}

export interface NewsResult {
  domain: string;
  news_items: NewsSignalItem[];
  executive_quotes: ExecutiveQuote[];
  urgency_signals: UrgencySignal[];
  sell_signals: string[];
}

/* ── Hiring card ── */
export interface BuyingCommitteeMember {
  name: string;
  title: string;
  tier: string;
  approach: string;
}

export interface ChampionSignal {
  person_name: string;
  signal: string;
  confidence: "high" | "medium" | "low";
}

export interface OpenRole {
  title: string;
  department: string;
  seniority: string;
}

export interface HiringResult {
  domain: string;
  total_roles: number;
  roles_by_tier: {
    tier1: number;
    tier2: number;
    tier3: number;
    tier4: number;
  };
  build_vs_buy_signal: "build" | "buy" | "mixed";
  buying_committee: BuyingCommitteeMember[];
  champion_signals: ChampionSignal[];
  open_roles: OpenRole[];
}

/* ── Social card ── */
export interface ExecutivePost {
  executive_name: string;
  post_summary: string;
  topic: string;
  algolia_relevance: string;
  date: string;
}

export interface QuotableStatement {
  statement: string;
  speaker: string;
  context: string;
}

export interface SocialResult {
  domain: string;
  executive_posts: ExecutivePost[];
  quotable_statements: QuotableStatement[];
  twitter_presence: boolean;
  company_social_summary: string;
}

/* ── Investor card ── */
export interface SaidVsFound {
  exec_said: string;
  we_found: string;
  competitors_doing: string;
  your_move: string;
}

export interface EarningsQuote {
  speaker: string;
  quote: string;
  date: string;
  context: string;
}

export interface BoardMember {
  name: string;
  background: string;
  is_tech_background: boolean;
}

export interface InvestorResult {
  domain: string;
  said_vs_found: SaidVsFound[];
  earnings_quotes: EarningsQuote[];
  board_members: BoardMember[];
  risk_factors: string[];
  sales_angles: string[];
}

/* ── Partner card ── */
export interface SIRelationship {
  partner_name: string;
  relationship_type: string;
  relevance: string;
}

export interface CoSellOpportunity {
  partner_name: string;
  opportunity: string;
  confidence: "high" | "medium" | "low";
}

export interface CaseStudy {
  customer_name: string;
  vertical: string;
  algolia_product: string;
  key_result: string;
}

export interface PartnerResult {
  domain: string;
  si_relationships: SIRelationship[];
  co_sell_opportunities: CoSellOpportunity[];
  case_studies: CaseStudy[];
  partner_play_recommendation: string;
  crossbeam_overlap_count: number | null;
}

/* ── Competitor matrix card ── */
export interface CompetitorScenario {
  company_name: string;
  domain: string;
  scenario: "GOLDEN" | "OFFENSIVE" | "DEFENSIVE" | "DISPLACEMENT";
}

export interface ComparisonDimension {
  dimension: string;
  prospect_score: number;
  competitor_scores: { company_name: string; score: number }[];
}

export interface CompetitorMatrixResult {
  domain: string;
  competitors: CompetitorScenario[];
  comparison_matrix: ComparisonDimension[];
  summary: string;
}

/* ── Industry card ── */
export interface IndustryBenchmark {
  metric: string;
  value: number;
  industry_avg: number;
  unit: string;
}

export interface PainPointMapping {
  pain_point: string;
  algolia_capability: string;
}

export interface IndustryCaseStudy {
  customer: string;
  vertical: string;
  result: string;
}

export interface IndustryResult {
  vertical: string;
  benchmarks: IndustryBenchmark[];
  trends: string[];
  pain_point_mapping: PainPointMapping[];
  case_studies: IndustryCaseStudy[];
}

/* ── Queries card ── */
export interface TestQuery {
  query: string;
  query_type: string;
  difficulty: "easy" | "medium" | "hard";
  expected_behavior: string;
}

export interface CompetitorQuerySet {
  company_name: string;
  domain: string;
  queries: TestQuery[];
}

export interface QueriesResult {
  domain: string;
  prospect_queries: TestQuery[];
  competitor_query_sets: CompetitorQuerySet[];
  query_count: number;
}

/* ── Browser audit card ── */
export interface DimensionScore {
  dimension: string;
  score: number;
  evidence: string;
}

export interface QueryResult {
  query: string;
  response_time_ms: number;
  result_count: number;
  has_autocomplete: boolean;
  has_facets: boolean;
}

export interface CompetitorBrowserResult {
  company_name: string;
  domain: string;
  dimension_scores: DimensionScore[];
}

export interface BrowserAuditResult {
  domain: string;
  dimension_scores: DimensionScore[];
  detected_search_provider: string | null;
  prospect_query_results: QueryResult[];
  total_queries_executed: number;
  total_screenshots: number;
  search_bar_found: boolean;
  competitor_results: CompetitorBrowserResult[];
}

/* ── Business case card ── */
export interface BusinessCaseSaidVsFound {
  exec_said: string;
  we_found: string;
  competitors_doing: string;
  your_move: string;
}

export interface ROILever {
  lever: string;
  conservative_value: number;
  moderate_value: number;
  unit: string;
}

export interface DisplacementModel {
  current_vendor: string;
  current_tco: number;
  algolia_tco: number;
  savings_3yr: number;
}

export interface TimingSignal {
  signal: string;
  urgency: "HIGH" | "MEDIUM" | "LOW";
}

export interface BusinessCaseResult {
  domain: string;
  said_vs_found: BusinessCaseSaidVsFound[];
  roi_levers: ROILever[];
  total_roi_conservative: number;
  total_roi_moderate: number;
  displacement_model: DisplacementModel;
  timing_signals: TimingSignal[];
}

/* ── Sales plays card ── */
export interface MEDDPICCItem {
  letter: string;
  name: string;
  person: string;
  evidence: string;
  approach: string;
}

export interface SPINQuestion {
  category: "situation" | "problem" | "implication" | "need_payoff";
  question: string;
}

export interface ObjectionHandler {
  objection: string;
  counter: string;
  evidence: string;
}

export interface PowerMapPerson {
  person: string;
  title: string;
  attitude: "champion" | "neutral" | "blocker";
  approach: string;
}

export interface TalkTrack {
  topic: string;
  track: string;
}

export interface SalesPlaysResult {
  domain: string;
  meddpicc: MEDDPICCItem[];
  spin_questions: SPINQuestion[];
  objection_handlers: ObjectionHandler[];
  power_map: PowerMapPerson[];
  talk_tracks: TalkTrack[];
}

/* ── Audit report card ── */
export interface ReportDimensionScore {
  dimension: string;
  score: number;
  evidence: string;
  severity: "critical" | "moderate" | "positive";
}

export interface PreCallBrief {
  search_score: number;
  top_angle: string;
  key_exec_to_reference: string;
  most_urgent_signal: string;
  recommended_first_play: string;
}

export interface LeaveBehind {
  search_quality_summary: string;
  competitive_benchmark: string;
  top_3_recommendations: string[];
  roi_summary: string;
}

export interface CompetitorScore {
  company_name: string;
  domain: string;
  overall_score: number;
}

export interface AuditReportResult {
  domain: string;
  company_name: string;
  dimension_scores: ReportDimensionScore[];
  overall_score: number;
  pre_call_brief: PreCallBrief;
  leave_behind: LeaveBehind;
  competitor_scores: CompetitorScore[];
}

/* ── Campaign card ── */
export interface EmailStep {
  step: number;
  label: string;
  subject: string;
  body: string;
}

export interface LinkedInMessage {
  recipient_name: string;
  recipient_title: string;
  connection_message: string;
  follow_up_message: string;
}

export interface CollateralScheduleItem {
  week: number;
  action: string;
  channel: string;
}

export interface CampaignResult {
  domain: string;
  email_sequence: EmailStep[];
  linkedin_messages: LinkedInMessage[];
  loom_script: string;
  collateral_schedule: CollateralScheduleItem[];
  competitor_messaging: string;
}

/* ── Factcheck card ── */
export interface Correction {
  claim_text: string;
  source_module: string;
  corrected_value: string;
  correction_reason: string;
}

export interface FactcheckResult {
  domain: string;
  verdict: "PROCEED" | "WARN" | "BLOCKED";
  total_claims: number;
  verified_count: number;
  plausible_count: number;
  unverified_count: number;
  contradicted_count: number;
  contradicted_pct: number;
  corrections: Correction[];
  summary: string;
}

/* ── Benchmarks card ── */
export interface BenchmarkEntry {
  vertical: string;
  metric_name: string;
  metric_value: Record<string, unknown>;
  sample_size: number;
  updated_at: string;
}

/* ── Audit stream SSE events ── */
export type AuditStreamEventType =
  | "connected"
  | "wave_started"
  | "module_started"
  | "module_completed"
  | "module_failed"
  | "wave_completed"
  | "audit_completed"
  | "timeout"
  | "error";

export interface AuditStreamEvent {
  event_type: AuditStreamEventType;
  timestamp: string;
  module_name?: string;
  wave?: number;
  status?: string;
  duration_ms?: number;
  summary?: string;
  error?: string;
  modules_in_wave?: string[];
  succeeded?: number;
  failed?: number;
  total_duration_ms?: number;
  audit_id?: string;
}

/* ── Company Intel v2 (intel-company module output) ── */

export type MeddpiccRole =
  | "economic_buyer"
  | "technical_buyer"
  | "champion"
  | "influencer"
  | "end_user";

export interface ExecutiveSeed {
  full_name: string;
  title: string;
  role_classification: MeddpiccRole | null;
  linkedin_url: string | null;
  tenure_description: string | null;
  previous_company: string | null;
}

export interface SubsidiarySeed {
  name: string;
  domain: string | null;
  description: string | null;
}

export interface CompetitorSeed {
  company_name: string;
  domain: string;
  why_competitor: string;
  ticker: string | null;
  linkedin_url: string | null;
}

export interface CompanyIntelOutput {
  legal_name: string;
  common_name: string;
  domain: string;
  headquarters: string;
  employee_count: number | null;
  employee_count_source: string | null;
  year_founded: number | null;
  business_model: string;
  industry: string;
  sub_vertical: string | null;
  is_public: boolean;
  ticker: string | null;
  parent_company: string | null;
  parent_domain: string | null;
  revenue_estimate: number | null;
  revenue_source: string | null;
  subsidiaries: SubsidiarySeed[];
  executives: ExecutiveSeed[];
  competitors: CompetitorSeed[];
  product_categories: string[];
  company_linkedin_url: string | null;
  twitter_handle: string | null;
  youtube_url: string | null;
  recent_headline: string | null;
}
