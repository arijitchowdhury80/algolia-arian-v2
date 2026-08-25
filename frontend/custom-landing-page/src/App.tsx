import { useEffect, useReducer, useRef, useState } from "react";
import { buildModules, CUST_LABEL, COMPMAP, PREFILL, type Module, type PickItem } from "./manifest";

const esc = (s: string) => (s || "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]!));
const itemLabel = (it: string | PickItem) => (typeof it === "string" ? it : it.t);
const field = (m: Module, k: string) => m.fields?.find((f) => f.k === k)?.v ?? "";
const fieldAsset = (m: Module, k: string) => m.fields?.find((f) => f.k === k)?.assetPath ?? "";
// Real Jahia asset binary, streamed through the backend proxy (token stays server-side).
const FILEAPI = "/api/jahia/file?path=";
const mediaHTML = (path: string) => /\.(mp4|webm|mov|m4v)$/i.test(path)
  ? `<video class="pv-media" src="${FILEAPI}${encodeURIComponent(path)}" autoplay muted loop playsinline controls preload="auto"></video>`
  : `<img class="pv-media" src="${FILEAPI}${encodeURIComponent(path)}" alt="" loading="lazy" />`;

function moduleValid(m: Module): boolean {
  if (m.kind === "standard") return true;
  if (m.fields) for (const f of m.fields) if (f.req && !(f.v || "").trim()) return false;
  if (m.pick) {
    const n = m.pick.chosen.length;
    if (m.pick.min != null && n < m.pick.min) return false;
    if (m.pick.max != null && n > m.pick.max) return false;
  }
  return true;
}
function summary(m: Module): string {
  if (m.kind === "standard") return "Standard — same on every page";
  if (m.pick) { const n = m.pick.chosen.length, cap = m.pick.max != null ? ` / ${m.pick.max}` : ""; return `${m.pick.label}: ${n}${cap} · ${m.variants![m.variant!]}`; }
  if (m.fields) { const h = (m.fields[0].v || "").trim(); return `${h ? `"${h.slice(0, 38)}${h.length > 38 ? "…" : ""}"` : "(empty)"} · ${m.variants![m.variant!]}`; }
  return "";
}
const chosen = (m: Module) => m.pick!.chosen.map((i) => m.pick!.items[i]).filter(Boolean);

// ---- live preview block HTML (per module, variant-conditional) ----
const BODY_MODULE_IDS = ["proven", "quotes", "features", "priorities", "resources"];
const HEADINGS: Record<string, string> = { proven: "Proven impact", quotes: "What customers say", features: "Continuous optimization", priorities: "Built around your priorities", resources: "Recommended resources" };
function bodyItems(m: Module): { title: string; meta?: string }[] {
  if (!m.pick) return [];
  return m.pick.chosen.map((i) => { const it = m.pick!.items[i]; return typeof it === "string" ? { title: it } : { title: it.t, meta: it.c }; }).filter((x) => x && x.title);
}
// Render a body module's content in the chosen Figma BODY layout (variant index 0-7).
function bodyLayoutHTML(m: Module, heading: string): string {
  const items = bodyItems(m);
  const label = (m.variants && m.variants[m.variant!]) || "";
  if (!items.length) return `<p class="pv-h">${heading}</p><p class="empty-note">Pick items to show…</p>`;
  const assetVal = m.fields && m.fields[0] && m.fields[0].v ? m.fields[0].v : "";
  // Real Jahia asset for this module (set when the operator browses one); else a labelled placeholder.
  const aPath = (m.fields && m.fields[0] && m.fields[0].assetPath) || "";
  const img = aPath ? mediaHTML(aPath) : `<div class="bl-img">▧</div>`;
  // Universal: a picked asset renders as a real banner in the head, for EVERY variant.
  const banner = aPath ? `<div class="pv-assetimg">${mediaHTML(aPath)}</div>` : "";
  const assetBar = assetVal && !aPath ? `<div class="pv-assets"><span>🖼 ${esc(assetVal)}</span></div>` : "";
  const head = `<p class="pv-h">${heading} <span class="empty-note">· ${esc(label)}</span></p>` + assetBar + banner;
  switch (m.variant) {
    case 0: return head + `<div class="bl-beside">${img}<div style="flex:1">${items.map((i) => `<div class="bl-row">${esc(i.title)}</div>`).join("")}</div></div>`;
    case 1: return head + items.map((i, n) => `<div class="lr ${n % 2 ? "r" : "l"}"><div class="lrimg">▧</div><div class="ptile" style="flex:1;margin:0">${i.meta ? `<small>${esc(i.meta)}</small>` : ""}${esc(i.title)}</div></div>`).join("");
    case 3: return head + `<ul class="bl-bul">${items.map((i) => `<li>${esc(i.title)}</li>`).join("")}</ul>`;
    case 4: return head + `<div class="fgrid">${items.map((i) => `<div class="bl-person"><div class="bl-av"></div><div>${esc(i.title)}${i.meta ? `<small>${esc(i.meta)}</small>` : ""}</div></div>`).join("")}</div>`;
    case 5: return head + items.map((i) => `<div class="bl-acc"><span>${esc(i.title)}</span><span>▾</span></div>`).join("");
    case 6: return head + `<div class="bl-beside"><div style="flex:1">${items.map((i) => `<div class="bl-acc"><span>${esc(i.title)}</span><span>▾</span></div>`).join("")}</div>${img}</div>`;
    case 7: return head + `${aPath ? mediaHTML(aPath) : `<div class="bl-video">▶ interactive demo</div>`}<div class="fgrid" style="margin-top:8px">${items.slice(0, 3).map((i) => `<div class="fc"><span class="i">◆</span>${esc(i.title)}</div>`).join("")}</div>`;
    default: return head + `<div class="fgrid">${items.map((i) => `<div class="fc"><span class="i">◆</span>${esc(i.title)}</div>`).join("")}</div>`; // case 2: 2/3/4 columns
  }
}
function previewInner(m: Module, brand: string): string {
  if (BODY_MODULE_IDS.includes(m.id)) return bodyLayoutHTML(m, HEADINGS[m.id]);
  if (m.id === "hero") {
    // 0 image+2CTAs · 1 single-col · 2 form single · 3 form two-col · 4 kelly-blue (Figma "Landing Page options")
    const v = m.variant ?? 0;
    const head = field(m, "headline") ? esc(field(m, "headline")) : '<span class="empty-note">Add a headline…</span>';
    const sub = esc(field(m, "subhead"));
    const mPath = fieldAsset(m, "media"), mName = field(m, "media");
    const bgPath = fieldAsset(m, "background");
    // real Jahia video when browsed; otherwise a labelled placeholder
    const media = mPath ? mediaHTML(mPath)
      : `<div class="pv-mediaph">${mName ? `🎬 ${esc(mName)}` : "▧ pick a hero video"}</div>`;
    // real background image → cover behind the hero (dark overlay for legible text)
    const heroStyle = bgPath ? ` style="background-image:linear-gradient(rgba(2,16,70,.58),rgba(2,16,70,.58)),url('${FILEAPI}${encodeURIComponent(bgPath)}');background-size:cover;background-position:center"` : "";
    const eyebrow = `<span class="eyebrow eyb">${esc(brand)} + Algolia</span>`;
    const formSingle = `<div class="pv-form">${["First name", "Last name", "Email", "Company"].map((l) => `<label>${l}</label><div class="pv-fi"></div>`).join("")}<span class="pv-btn p" style="margin-top:6px">Get the report</span></div>`;
    const formTwo = `<div class="pv-formcard"><p class="pv-fh">Download the report</p><div class="pv-fgrid">${["First name", "Last name", "Email", "Company"].map((l) => `<div><label>${l}</label><div class="pv-fi d"></div></div>`).join("")}</div><span class="pv-btn p" style="margin-top:10px">Get the report</span></div>`;
    if (v === 4) return `<div class="pv-hero solid center"${heroStyle}>${eyebrow}<h3 class="big">${head}</h3><p>${sub}</p><div class="pv-btns center"><span class="pv-btn p">Request demo</span></div></div>`;
    if (v === 1) return `<div class="pv-hero center"${heroStyle}>${eyebrow}<h3>${head}</h3><p>${sub}</p>${(mPath || mName) ? `<div class="pv-mediawrap">${media}</div>` : ""}</div>`;
    if (v === 2) return `<div class="pv-hero split"${heroStyle}><div class="pv-hcol">${eyebrow}<h3>${head}</h3><p>${sub}</p></div><div class="pv-hcol">${formSingle}</div></div>`;
    if (v === 3) return `<div class="pv-hero split"${heroStyle}><div class="pv-hcol">${eyebrow}<h3>${head}</h3><p>${sub}</p></div><div class="pv-hcol">${formTwo}</div></div>`;
    return `<div class="pv-hero split"${heroStyle}><div class="pv-hcol">${eyebrow}<h3>${head}</h3><p>${sub}</p><div class="pv-btns"><span class="pv-btn p">Request demo</span><span class="pv-btn s">Get started</span></div></div><div class="pv-hcol media">${media}</div></div>`;
  }
  // proven / quotes / features / priorities / resources all render via bodyLayoutHTML (routed at top).
  if (m.id === "search") return `<div class="pv-std">Search that delivers · integrations &nbsp;<b>(standard)</b></div>`;
  if (m.id === "awards") return `<div class="pv-std">Award-winning search & product discovery &nbsp;<b>(standard)</b></div>`;
  if (m.id === "parting") {
    const plain = m.variant === 0; // 0 = Plain CTA footer, 1 = Alt (gradient) footer
    const bg = field(m, "bg");
    const bgPath = fieldAsset(m, "bg");
    const bgStyle = bgPath ? ` style="background-image:linear-gradient(rgba(2,16,70,.72),rgba(2,16,70,.72)),url('${FILEAPI}${encodeURIComponent(bgPath)}');background-size:cover;background-position:center"` : "";
    return `<div class="pv-cta${plain ? " plain" : ""}"${bgStyle}><h3>${esc(brand)} + Algolia</h3>`
      + `<p style="color:#c3cdf5;font-size:12.5px">${field(m, "message") ? esc(field(m, "message")) : '<span class="empty-note" style="color:#9fb4ff">Add a parting message…</span>'}</p>`
      + (field(m, "cta") ? `<span class="pv-btn p" style="display:inline-block;margin-top:12px">${esc(field(m, "cta"))}</span>` : "")
      + `<div class="ae">${field(m, "ae") ? "Your AE: " + esc(field(m, "ae")) : ""}</div>`
      + (bg && !bgPath ? `<div class="pv-assets" style="justify-content:center">🖼 ${esc(bg)}</div>` : "")
      + `</div>`;
  }
  return "";
}

// Real Jahia page paths per customer (LIVE workspace). "new" has no page yet.
const PAGE_PATH: Record<string, string> = {
  "ralph-lauren": "/sites/www/home/lp/ralph-lauren-algolia",
  "belk": "/sites/www/home/lp/belk-algolia",
};

const MARK = "M250,0C113.38,0,2,110.16,.03,246.32c-2,138.29,110.19,252.87,248.49,253.67,42.71,.25,83.85-10.2,120.38-30.05,3.56-1.93,4.11-6.83,1.08-9.52l-23.39-20.74c-4.75-4.22-11.52-5.41-17.37-2.92-25.5,10.85-53.21,16.39-81.76,16.04-111.75-1.37-202.04-94.35-200.26-206.1,1.76-110.33,92.06-199.55,202.8-199.55h202.83V407.68l-115.08-102.25c-3.72-3.31-9.43-2.66-12.43,1.31-18.47,24.46-48.56,39.67-81.98,37.36-46.36-3.2-83.92-40.52-87.4-86.86-4.15-55.28,39.65-101.58,94.07-101.58,49.21,0,89.74,37.88,93.97,86.01,.38,4.28,2.31,8.28,5.53,11.13l29.97,26.57c3.4,3.01,8.8,1.17,9.63-3.3,2.16-11.55,2.92-23.6,2.07-35.95-4.83-70.39-61.84-127.01-132.26-131.35-80.73-4.98-148.23,58.18-150.37,137.35-2.09,77.15,61.12,143.66,138.28,145.36,32.21,.71,62.07-9.42,86.2-26.97l150.36,133.29c6.45,5.71,16.62,1.14,16.62-7.48V9.49C500,4.25,495.75,0,490.51,0H250Z";

export default function App() {
  const [cust, setCust] = useState("ralph-lauren");
  const [modules, setModules] = useState<Module[]>(() => buildModules("ralph-lauren"));
  const [mode, setMode] = useState<"scroll" | "guide">("scroll");
  const [pvMode, setPvMode] = useState<"build" | "jahia">("build");
  const [guideIdx, setGuideIdx] = useState(0);
  const [sel, setSel] = useState("hero");
  const [lib, setLib] = useState<string[] | null>(null);
  const [libStatus, setLibStatus] = useState("Loading component library…");
  const [toast, setToast] = useState("");
  const [, force] = useReducer((x) => x + 1, 0);
  const toastTimer = useRef<number>();
  const isDev = typeof location !== "undefined" && location.hash === "#dev";

  const showToast = (m: string) => { setToast(m); window.clearTimeout(toastTimer.current); toastTimer.current = window.setTimeout(() => setToast(""), 2200); };
  const changeMods = modules.filter((m) => m.kind === "change");
  const brand = PREFILL[cust].title;

  // load the live Jahia component library from the standalone backend (token stays server-side)
  useEffect(() => {
    fetch("/api/jahia/components").then((r) => r.json()).then((j) => {
      if (!j.ok) throw new Error(j.error || "failed");
      setLib(j.components);
      const total = Object.keys(COMPMAP).length;
      const matched = Object.values(COMPMAP).filter((c) => j.components.includes(c)).length;
      setLibStatus(`Jahia component library connected · ${j.count} components · ${matched}/${total} modules backed`);
    }).catch((e) => setLibStatus(`Component library offline — ${e.message}`));
  }, []);

  function loadCustomer(c: string) {
    setCust(c); setModules(buildModules(c)); setSel(mode === "guide" ? "hero" : "hero"); setGuideIdx(0);
    if (c === "new") showToast("New account — fields start empty. Nothing is invented.");
  }
  function setVariant(m: Module, i: number) { m.variant = i; force(); }
  function editField(m: Module, i: number, v: string) { m.fields![i].v = v; force(); }
  function togglePick(m: Module, idx: number) {
    const at = m.pick!.chosen.indexOf(idx);
    if (at >= 0) m.pick!.chosen.splice(at, 1);
    else { if (m.pick!.max != null && m.pick!.chosen.length >= m.pick!.max) { showToast(`Max ${m.pick!.max} — remove one first`); return; } m.pick!.chosen.push(idx); }
    force();
  }
  function addCustom(m: Module, val: string) {
    val = val.trim(); if (!val) return;
    if (m.pick!.max != null && m.pick!.chosen.length >= m.pick!.max) { showToast(`Max ${m.pick!.max} reached`); return; }
    m.pick!.items.push(m.pick!.grouped ? { t: val, c: "Custom" } : val);
    m.pick!.chosen.push(m.pick!.items.length - 1); force(); showToast(`Added "${val}"`);
  }
  // drag reorder
  const dragId = useRef<string | null>(null);
  function onDrop(targetId: string) {
    const d = dragId.current; if (!d || d === targetId) return;
    const from = modules.findIndex((m) => m.id === d), to = modules.findIndex((m) => m.id === targetId);
    const next = [...modules]; const [it] = next.splice(from, 1); next.splice(to, 0, it);
    next.forEach((m, i) => (m.order = i + 1)); setModules(next); showToast(`Moved “${it.name}” to position ${to + 1}`);
  }

  const invalid = modules.filter((m) => m.kind === "change" && !moduleValid(m));
  const railList = mode === "guide" ? [changeMods[guideIdx]].filter(Boolean) : modules;

  function preview() {
    if (invalid.length) { showToast("Fix first: " + invalid.map((m) => m.name).join(", ")); setSel(invalid[0].id); if (mode === "guide") setGuideIdx(changeMods.findIndex((m) => m.id === invalid[0].id)); }
    else showToast("Preview valid — full render would open via Jahia (read-only). Wiring pending.");
  }

  // ---- browse modals (assets locked to DAM folders; components from the allowlist) ----
  type BrowseState = { mode: "asset" | "component"; title: string; kind?: string; mid?: string; fidx?: number; items: any[]; folders: any[]; path?: string; root?: string };
  const [browse, setBrowse] = useState<BrowseState | null>(null);
  const [bq, setBq] = useState("");
  async function openAssetBrowse(mod: Module, fidx: number, kind: string) {
    setBrowse({ mode: "asset", title: `Browse ${kind}s — ${mod.name}`, kind, mid: mod.id, fidx, items: [], folders: [] });
    const r = await fetch(`/api/jahia/assets?kind=${kind}`).then((x) => x.json()).catch(() => ({ ok: false, error: "network" }));
    if (r.ok) setBrowse((b) => (b ? { ...b, items: r.files, folders: r.folders, path: r.path, root: r.root } : b));
    else showToast("Asset browse: " + (r.error || "failed"));
  }
  async function drill(path: string) {
    const k = browse?.kind; if (!k) return;
    const r = await fetch(`/api/jahia/assets?kind=${k}&path=${encodeURIComponent(path)}`).then((x) => x.json()).catch(() => ({ ok: false }));
    if (r.ok) setBrowse((b) => (b ? { ...b, items: r.files, folders: r.folders, path: r.path } : b));
  }
  function openComponentBrowse() { setBq(""); setBrowse({ mode: "component", title: "Jahia component library", items: lib || [], folders: [] }); }
  function pickAsset(f: { name: string; path: string }) {
    if (browse?.mid != null && browse.fidx != null) { const m = modules.find((x) => x.id === browse.mid); if (m) { m.fields![browse.fidx].v = f.name; m.fields![browse.fidx].assetPath = f.path; force(); } }
    setBrowse(null); showToast(`Set “${f.name}”`);
  }

  return (
    <>
      <header className="hero">
        <span className="blob b1" /><span className="blob b2" /><span className="blob b3" />
        <div className="row1">
          <div className="brand">
            <svg viewBox="0 0 500 500.34" aria-hidden="true"><path d={MARK} /></svg>
            Algolia<span className="divx" /><span className="t">Whale Page Builder</span>
          </div>
          <div className="spacer" />
          <div className="cust">
            <label htmlFor="cust">Customer</label>
            <select id="cust" value={cust} onChange={(e) => loadCustomer(e.target.value)}>
              <option value="ralph-lauren">Ralph Lauren</option>
              <option value="belk">Belk</option>
              <option value="new">＋ New account…</option>
            </select>
          </div>
          <div className="modeswitch" role="group" aria-label="Builder mode">
            <button aria-pressed={mode === "scroll"} onClick={() => { setMode("scroll"); setGuideIdx(0); }}>All modules</button>
            <button aria-pressed={mode === "guide"} onClick={() => { setMode("guide"); setGuideIdx(0); setSel(changeMods[0].id); }}>Guide me</button>
          </div>
          <button className="iconbtn" aria-label="Toggle dark mode" onClick={() => { const r = document.documentElement; r.setAttribute("data-theme", r.getAttribute("data-theme") === "dark" ? "light" : "dark"); }}>◐</button>
        </div>
        <div className="row2">
          <h1><span className="sm">Whale one-to-one</span>{brand}</h1>
          <div className="stats">
            <div className="stat"><div className="n">9</div><div className="l">Modules</div></div>
            <div className="stat"><div className="n blue">7</div><div className="l">Tailored</div></div>
            <div className="stat"><div className="n">2</div><div className="l">Standard</div></div>
          </div>
        </div>
      </header>

      <div className="app">
        <section className="rail" aria-label="Module list">
          <div className="libbar" onClick={openComponentBrowse} style={{ cursor: "pointer" }} title="Browse the live Jahia component library">
            <span className={"dotp " + (lib ? "ok" : "load")} />{libStatus}
            {lib && <span style={{ marginLeft: "auto", color: "var(--blue)", fontWeight: 600 }}>Browse ›</span>}
          </div>
          <div className="railhead"><span className="eyebrow">The page · drag ⠿ to reorder</span>{mode === "guide" && <span className="eyebrow" style={{ color: "var(--blue)" }}>Step {guideIdx + 1} of {changeMods.length}</span>}</div>
          <div className="spine">
            {railList.map((m, i) => {
              const locked = m.kind === "standard";
              const selc = m.id === sel && !locked ? " sel" : "";
              return (
                <div key={m.id} className={`node ${locked ? "locked" : "change"}${selc}`} draggable={mode === "scroll"}
                  onDragStart={() => (dragId.current = m.id)} onDragOver={(e) => { if (dragId.current) e.preventDefault(); }}
                  onDrop={(e) => { e.preventDefault(); onDrop(m.id); dragId.current = null; }} onDragEnd={() => (dragId.current = null)}>
                  <span className="dot">{locked ? "🔒" : i + 1}</span>
                  <div className="ncard">
                    <div className="nhead" onClick={() => !locked && setSel(m.id)}>
                      {mode === "scroll" && <span className="grip" title="Drag to reorder">⠿</span>}
                      {!locked && <span className={"vflag " + (moduleValid(m) ? "ok" : "warn")}>{moduleValid(m) ? "✓" : "!"}</span>}
                      <span className="nname">{m.name}</span>
                      {locked ? <span className="chip std">standard</span> : <>
                        <span className="chip brand">tailored</span>
                        {m.pick && <span className="chip pick">{m.pick.max != null ? `pick ${m.pick.min || 0}–${m.pick.max}` : "pick-list"}</span>}
                        {m.optional && <span className="chip std">optional</span>}
                      </>}
                      {locked && <span className="lock">🔒</span>}
                    </div>
                    <div className="nsum">{summary(m)}</div>
                    {!locked && m.id === sel && <Editor m={m} lib={lib} isDev={isDev} onVariant={setVariant} onField={editField} onPick={togglePick} onAdd={addCustom} onBrowse={openAssetBrowse} />}
                  </div>
                </div>
              );
            })}
          </div>
          {mode === "guide" && (
            <div className="guidenav">
              <button className="btn" disabled={guideIdx === 0} onClick={() => { const n = guideIdx - 1; setGuideIdx(n); setSel(changeMods[n].id); }}>‹ Back</button>
              <button className="btn primary" onClick={() => { if (guideIdx < changeMods.length - 1) { const n = guideIdx + 1; setGuideIdx(n); setSel(changeMods[n].id); } else showToast("All tailored modules reviewed"); }}>{guideIdx === changeMods.length - 1 ? "Done" : "Next ›"}</button>
            </div>
          )}
        </section>

        <section className="canvas" aria-label="Live preview">
          <div className="pvswitch" role="group" aria-label="Preview mode">
            <button aria-pressed={pvMode === "build"} onClick={() => setPvMode("build")}>Build view</button>
            <button aria-pressed={pvMode === "jahia"} onClick={() => setPvMode("jahia")}>True preview (Jahia)</button>
          </div>
          <div className="device">
            <div className="chrome"><span className="d" /><span className="d" /><span className="d" /><span className="url">algolia.com/lp/{cust === "new" ? "new-account" : cust}-algolia</span></div>
            {pvMode === "jahia" ? (
              PAGE_PATH[cust]
                ? <iframe className="screen jahia" title="Jahia rendered preview" src={`/api/jahia/render?path=${encodeURIComponent(PAGE_PATH[cust])}`} />
                : <div className="screen"><p className="empty-note" style={{ padding: 24 }}>No published Jahia page for this customer yet. Pick Ralph Lauren or Belk to see the real rendered page, or build one first.</p></div>
            ) : (
              <div className="screen">
                {modules.map((m) => (
                  <div key={m.id} className={"blk" + (m.id === sel ? " active" : "")} dangerouslySetInnerHTML={{ __html: '<span class="plabel">editing</span>' + previewInner(m, brand) }} />
                ))}
              </div>
            )}
          </div>
        </section>
      </div>

      <div className="bar"><div className="inner">
        <span className={"status " + (invalid.length ? "blocked" : "ready")}><span className="d" />{invalid.length ? `${invalid.length} module${invalid.length > 1 ? "s" : ""} need attention` : "All modules valid"}</span>
        <span className="note">Live preview mirrors Jahia render. Publish pushes into Jahia — governance-gated.</span>
        <button className="btn" onClick={preview}>Open full preview</button>
        <button className="btn primary" disabled title="Governance pending">Publish to Jahia</button>
      </div></div>

      <div className={"toast" + (toast ? " show" : "")}>{toast}</div>

      {browse && (
        <div className="modal-overlay" onClick={() => setBrowse(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-head"><b>{browse.title}</b><button className="modal-x" onClick={() => setBrowse(null)}>✕</button></div>
            {browse.mode === "component" ? (
              <>
                <input className="modal-search" placeholder="Search components…" value={bq} onChange={(e) => setBq(e.target.value)} autoFocus />
                <div className="modal-list">
                  {(browse.items as string[]).filter((c) => c.toLowerCase().includes(bq.toLowerCase())).map((c) => (
                    <button key={c} className="modal-item mono" onClick={() => { showToast("Component: " + c); setBrowse(null); }}>{c}</button>
                  ))}
                </div>
                <div className="modal-foot">{(browse.items as string[]).length} components · live from Jahia /sites/www allowlist</div>
              </>
            ) : (
              <>
                <div className="modal-path">📁 {(browse.path || browse.root || "").replace(browse.root || "", "") || "/"}<span className="modal-lock">locked to {browse.root}</span></div>
                <div className="modal-list">
                  {browse.path && browse.root && browse.path !== browse.root && <button className="modal-item folder" onClick={() => drill(browse.root!)}>↩ up</button>}
                  {(browse.folders || []).map((f: any) => <button key={f.path} className="modal-item folder" onClick={() => drill(f.path)}>📁 {f.name}</button>)}
                  {(browse.items || []).map((f: any) => <button key={f.path} className="modal-item" onClick={() => pickAsset(f)}>🖼 {f.name}</button>)}
                  {!(browse.folders || []).length && !(browse.items || []).length && <div className="empty-note" style={{ padding: 14 }}>Loading…</div>}
                </div>
                <div className="modal-foot">Approved assets only — locked to {browse.root}</div>
              </>
            )}
          </div>
        </div>
      )}
    </>
  );
}

function Editor({ m, lib, isDev, onVariant, onField, onPick, onAdd, onBrowse }: {
  m: Module; lib: string[] | null; isDev: boolean;
  onVariant: (m: Module, i: number) => void; onField: (m: Module, i: number, v: string) => void;
  onPick: (m: Module, i: number) => void; onAdd: (m: Module, v: string) => void;
  onBrowse: (m: Module, i: number, kind: string) => void;
}) {
  const [add, setAdd] = useState("");
  const comp = COMPMAP[m.id];
  const cats = m.pick?.grouped ? [...new Set((m.pick.items as PickItem[]).map((x) => x.c))] : [];
  const n = m.pick?.chosen.length ?? 0;
  let cnt = ""; let over = false;
  if (m.pick) {
    cnt = `Selected ${n}${m.pick.max != null ? ` / ${m.pick.max}` : ""}`;
    if (m.pick.max != null && n > m.pick.max) { cnt = `Over the max — remove ${n - m.pick.max}`; over = true; }
    else if (m.pick.min != null && n < m.pick.min) { cnt = `Pick at least ${m.pick.min} (have ${n})`; over = true; }
  }
  const chip = (i: number, label: string) => (
    <button key={i} className="pk" aria-pressed={m.pick!.chosen.includes(i)} onClick={() => onPick(m, i)}>
      {(m.pick!.chosen.includes(i) ? "✓ " : "＋ ") + label}
    </button>
  );
  return (
    <div className="editor">
      <p className="eyebrow first">Layout</p>
      <div className="variants">
        {m.variants!.map((v, i) => (
          <button key={i} className="variant" aria-pressed={i === m.variant} onClick={() => onVariant(m, i)}>
            <div className="th">{m.thumbs?.[i] ? <img className="vthumb" src={m.thumbs[i]} alt={v} /> : "▧"}</div>
            <div className="vl">{v}</div>
          </button>
        ))}
      </div>
      {isDev && comp && <div style={{ fontSize: 11, color: lib?.includes(comp) ? "#0a8f6f" : "var(--amber)", marginBottom: 12 }}>Jahia component: <code>{comp}</code>{lib ? (lib.includes(comp) ? " · ✓ live" : " · ⚠ not in allowlist") : ""}</div>}
      {m.fields && <>
        <p className="eyebrow">Content</p>
        {m.fields.map((f, i) => (
          <div className="fld" key={f.k}>
            <label>{f.label}{f.req ? " *" : ""}{f.asset ? <span className="assettag"> · {f.asset}</span> : null}</label>
            {f.asset ? (
              <div className="fld-row">
                <input value={f.v} placeholder="none selected — Browse…" onChange={(e) => onField(m, i, e.target.value)} />
                <button type="button" className="browsebtn" onClick={() => onBrowse(m, i, f.asset!)}>Browse…</button>
              </div>
            ) : f.area
              ? <textarea className={f.req && !f.v.trim() ? "err" : ""} value={f.v} onChange={(e) => onField(m, i, e.target.value)} />
              : <input className={f.req && !f.v.trim() ? "err" : ""} value={f.v} onChange={(e) => onField(m, i, e.target.value)} />}
          </div>
        ))}
      </>}
      {m.pick && <>
        <p className="eyebrow">{m.pick.label}{m.pick.max != null ? ` — pick ${m.pick.min || 0}–${m.pick.max}` : ""}</p>
        <div className="picker">
          {m.pick.grouped
            ? cats.map((c) => [<div className="cat" key={c}>{c}</div>, ...(m.pick!.items as PickItem[]).map((it, i) => it.c === c ? chip(i, it.t) : null)])
            : m.pick.items.map((it, i) => chip(i, itemLabel(it)))}
        </div>
        <div className="addrow">
          <input placeholder="Add custom…" value={add} onChange={(e) => setAdd(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") { onAdd(m, add); setAdd(""); } }} />
          <button className="addbtn" onClick={() => { onAdd(m, add); setAdd(""); }}>Add</button>
        </div>
        <div className={"cnt" + (over ? " over" : "")}>{cnt}</div>
      </>}
    </div>
  );
}
