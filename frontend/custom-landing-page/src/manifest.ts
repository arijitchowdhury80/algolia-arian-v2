// The 9-module manifest + per-customer pre-fill. Mirrors the validated prototype.
// Hero variant thumbnails are the real Figma "Landing Page options" designs (file 5DkPHASwX5HwFgG0WFEDhS,
// Banners frame 12:17), downloaded to src/assets/figma/banners/.
import heroImg2cta from "./assets/figma/banners/banner-1-hero-image-two-ctas.png";
import heroSingleCol from "./assets/figma/banners/banner-2-single-col-title-subtitle.png";
import heroFormSingle from "./assets/figma/banners/banner-3-form-hero-single-col.png";
import heroFormTwoCol from "./assets/figma/banners/banner-4-form-hero-two-col.png";
import heroKellyBlue from "./assets/figma/banners/banner-5-hero-kelly-blue.png";
import body1 from "./assets/figma/body/body-1-forms-image-or-text-beside.png";
import body2 from "./assets/figma/body/body-2-left-right-bg-options.png";
import body3 from "./assets/figma/body/body-3-columns-2-3-4.png";
import body4 from "./assets/figma/body/body-4-single-col-bullets.png";
import body5 from "./assets/figma/body/body-5-people-cards.png";
import body6 from "./assets/figma/body/body-6-accordions.png";
import body7 from "./assets/figma/body/body-7-accordion-image-swap.png";
import body8 from "./assets/figma/body/body-8-video-demo.png";
import footer1 from "./assets/figma/footer/footer-1-plain-cta.png";
import footer2 from "./assets/figma/footer/footer-2-alt.png";

export type Kind = "change" | "standard";
export interface FieldDef { k: string; label: string; v: string; req?: boolean; area?: boolean; asset?: "video" | "image" | "logo"; assetPath?: string }
export interface PickItem { t: string; c: string }
export interface PickDef {
  label: string; min?: number; max?: number; grouped?: boolean;
  items: (string | PickItem)[]; chosen: number[];
}
export interface Module {
  id: string; order: number; name: string; kind: Kind; optional?: boolean;
  variants?: string[]; variant?: number; fields?: FieldDef[]; pick?: PickDef; thumbs?: string[];
}

// Real Figma hero variants (Banners frame). Order matches thumbs below.
export const HERO_VARIANTS = [
  "Hero + image, 2 CTAs",
  "Single column title + subtitle",
  "Form in hero, single column",
  "Form in hero, two-column",
  "Kelly-blue background",
];
const HERO_THUMBS = [heroImg2cta, heroSingleCol, heroFormSingle, heroFormTwoCol, heroKellyBlue];

// Real Figma BODY layout options (Body frame #12:25) — the palette every body module picks from.
export const BODY_VARIANTS = [
  "Forms with image/text beside",
  "Left / right (bg options)",
  "2 / 3 / 4 columns",
  "Single column with bullets",
  "People cards",
  "Accordions",
  "Accordions, image swap",
  "Video / interactive demo",
];
const BODY_THUMBS = [body1, body2, body3, body4, body5, body6, body7, body8];

// Real Figma FOOTER options (Footer frame #12:74).
export const FOOTER_VARIANTS = ["Plain CTA footer", "Alt footer design"];
const FOOTER_THUMBS = [footer1, footer2];

export const CUST_LABEL: Record<string, string> = {
  "ralph-lauren": "Ralph Lauren", belk: "Belk", new: "New account",
};
// module -> backing Jahia component type (validated against the live allowlist; dev-only display).
export const COMPMAP: Record<string, string> = {
  hero: "aant:algoliaBanner", proven: "aant:statisticCardTeaser", quotes: "aant:algoliaTeaser",
  features: "aant:algoliaFeatureCard", priorities: "aant:algoliaTeaser", resources: "aant:algoliaTeaser",
  parting: "aant:algoliaTeaser",
};

const PROOF = ["Forrester TEI", "Conversion +34%", "AOV +18%", "Latency <20ms", "Global scale ✓", "Zero-results ↓"];
const QUOTES = ['"Algolia transformed discovery"', '"Search that just works"', '"Measurable revenue lift"', '"Fast to deploy"', '"Best-in-class relevance"'];
const FEATURES = ["NeuralSearch", "Recommend", "Merchandising", "Analytics", "Personalization", "Browse", "Ask AI", "Agent Studio", "Synonyms", "Redirects", "Query rules", "Insights"];
const PRIOR: PickItem[] = [
  { t: "Conversion lift", c: "Revenue" }, { t: "Higher AOV", c: "Revenue" }, { t: "Merchandiser time", c: "Efficiency" },
  { t: "Ops cost", c: "Efficiency" }, { t: "Multi-region", c: "Global" }, { t: "Localized relevance", c: "Global" }, { t: "Faster launches", c: "Efficiency" },
];
const RES = ["eBook", "Webinar", "Case study", "Blog", "Report"];

interface Prefill {
  title: string;
  hero: { headline: string; subhead: string; video: string; lockup: string };
  proof: number[]; quotes: number[]; features: number[]; priorities: number[]; resources: number[];
  parting: { message: string; cta: string; ae: string };
}
export const PREFILL: Record<string, Prefill> = {
  "ralph-lauren": {
    title: "Ralph Lauren",
    hero: { headline: "Increase conversion at a global scale", subhead: "Deliver faster, more relevant, consistent discovery", video: "RL runway film", lockup: "Ralph Lauren × Algolia" },
    proof: [0, 1, 2], quotes: [0, 1, 2], features: [0, 1, 2, 3, 4, 5, 6, 7, 8], priorities: [0, 1, 4], resources: [0, 1, 2],
    parting: { message: "Create a search experience that performs at the scale your brand demands", cta: "Get started", ae: "Tariq Khan" },
  },
  belk: {
    title: "Belk",
    hero: { headline: "Increase revenue with future-forward AI product discovery", subhead: "Personalized shopping that scales with your catalog", video: "Belk lifestyle film", lockup: "Belk × Algolia" },
    proof: [0, 2, 3], quotes: [1, 3], features: [0, 1, 3, 4, 6, 7, 8, 9], priorities: [1, 2, 5], resources: [0, 2],
    parting: { message: "A future-forward search and product discovery experience for Belk shoppers", cta: "Book a demo", ae: "Nicole Mills" },
  },
  new: {
    title: "New account",
    hero: { headline: "", subhead: "", video: "", lockup: "" },
    proof: [], quotes: [], features: [], priorities: [], resources: [],
    parting: { message: "", cta: "", ae: "" },
  },
};

export function buildModules(cust: string): Module[] {
  const p = PREFILL[cust];
  return [
    { id: "hero", order: 1, name: "Hero", kind: "change", variants: [...HERO_VARIANTS], variant: 0, thumbs: [...HERO_THUMBS],
      fields: [{ k: "headline", label: "Headline", v: p.hero.headline, req: true }, { k: "subhead", label: "Subhead", v: p.hero.subhead, req: true }, { k: "media", label: "Hero video", v: p.hero.video, asset: "video" }, { k: "background", label: "Background image", v: "", asset: "image" }] },
    { id: "proven", order: 2, name: "Proven Impact", kind: "change", variants: [...BODY_VARIANTS], variant: 2, thumbs: [...BODY_THUMBS],
      fields: [{ k: "logos", label: "Proof / customer logos", v: "", asset: "logo" }],
      pick: { label: "Proof points", min: 1, max: 6, items: [...PROOF], chosen: [...p.proof] } },
    { id: "quotes", order: 3, name: "Customer Quotes", kind: "change", variants: [...BODY_VARIANTS], variant: 4, thumbs: [...BODY_THUMBS],
      fields: [{ k: "logos", label: "Customer logos", v: "", asset: "logo" }],
      pick: { label: "Quotes", min: 1, max: 5, items: [...QUOTES], chosen: [...p.quotes] } },
    { id: "features", order: 4, name: "Features / Solutions", kind: "change", variants: [...BODY_VARIANTS], variant: 2, thumbs: [...BODY_THUMBS],
      fields: [{ k: "icons", label: "Feature icons / imagery", v: "", asset: "image" }],
      pick: { label: "Features", min: 8, max: 10, items: [...FEATURES], chosen: [...p.features] } },
    { id: "priorities", order: 5, name: "Built Around Your Priorities", kind: "change", variants: [...BODY_VARIANTS], variant: 1, thumbs: [...BODY_THUMBS],
      fields: [{ k: "image", label: "Section imagery", v: "", asset: "image" }],
      pick: { label: "Priorities", min: 1, max: 7, grouped: true, items: PRIOR.map((x) => ({ ...x })), chosen: [...p.priorities] } },
    { id: "search", order: 6, name: "Search That Delivers / Integrations", kind: "standard" },
    { id: "resources", order: 7, name: "Recommended Resources", kind: "change", optional: true, variants: [...BODY_VARIANTS], variant: 2, thumbs: [...BODY_THUMBS],
      fields: [{ k: "thumb", label: "Resource thumbnails", v: "", asset: "image" }],
      pick: { label: "Resources", min: 0, max: 5, items: [...RES], chosen: [...p.resources] } },
    { id: "awards", order: 8, name: "Award-Winning Search & Product Discovery", kind: "standard" },
    { id: "parting", order: 9, name: "Parting Shot / Final CTA", kind: "change", variants: [...FOOTER_VARIANTS], variant: 0, thumbs: [...FOOTER_THUMBS],
      fields: [{ k: "message", label: "Message", v: p.parting.message, req: true, area: true }, { k: "cta", label: "CTA text", v: p.parting.cta, req: true }, { k: "ae", label: "AE / BDR name", v: p.parting.ae, req: true }, { k: "bg", label: "Background image", v: "", asset: "image" }] },
  ];
}
