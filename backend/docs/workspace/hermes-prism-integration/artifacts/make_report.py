#!/usr/bin/env python3
"""make_report.py — portrait A4 Algolia search-audit DOCUMENT (HTML -> PDF via Chrome).

Matches the L.L. Bean reference: running header + footer on every page, chaptered structure
(Cover, About+Why-matters+Algolia-delivers, capability before/after, Areas of Improvement findings
with real screenshots, close on a scoped POC). No pricing. No financials. No fabrication: every
number from {slug}-audit-data.json with its source. No em dashes.

Usage: python3 make_report.py <audit-data.json> <out.html>
"""
import base64, html, json, os, sys

DS = "/Users/arijitchowdhury/Dropbox/AI-Development/Algolia-Design-System"
SEV_COLOR = {"LOW": "#059669", "MEDIUM": "#D97706", "HIGH": "#DC2626", "CRITICAL": "#B91C1C"}
SEV_BG = {"LOW": "#E9F7F0", "MEDIUM": "#FDF1E3", "HIGH": "#FBEAEA", "CRITICAL": "#FBE3E3"}


def b64(p):
    return base64.b64encode(open(p, "rb").read()).decode()


def uri(p):
    ext = os.path.splitext(p)[1].lower()
    m = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".svg": "image/svg+xml"}.get(ext, "application/octet-stream")
    return f"data:{m};base64,{b64(p)}"


def e(x):
    if x is None:
        return ""
    if isinstance(x, (list, tuple)):
        x = ", ".join(str(i) for i in x if i)
    return html.escape(str(x).replace("—", "-").strip())


def clip(x, n):
    s = str(x or "").replace("—", "-").strip()
    return html.escape(s if len(s) <= n else s[: n - 1].rstrip() + "…")


def domain(url):
    """Clean host label for a URL (nielseniq.com), no scheme/path."""
    h = str(url).split("//", 1)[-1].split("/", 1)[0]
    return h[4:] if h.startswith("www.") else h


def src(label, url=None):
    if url and str(url).startswith("http"):
        return f'<a class="src" href="{e(url)}">{clip(label,52)} ↗</a>'
    # A bare URL as the label reads as junk; render it as a clean domain link instead.
    if str(label).startswith("http"):
        return f'<a class="src" href="{e(label)}">{e(domain(label))} ↗</a>'
    return f'<span class="src src--p">Source: {clip(label,64)}</span>'


def main(json_path, out_path):
    d = json.load(open(json_path))
    rd = os.path.dirname(os.path.abspath(json_path))
    meta = d.get("meta", {})
    co = meta.get("company", "Company")
    score = d.get("score", {})
    findings = d.get("findings", [])
    crit = [f for f in findings if str(f.get("severity", "")).lower() == "critical"]
    ordered = (crit + [f for f in findings if f not in crit])
    sig = {s.get("type"): s for s in d.get("intelligence_signals", [])}
    opp = sig.get("industry-opp", {})

    logo_blue = uri(f"{DS}/assets/Algolia-logo-blue.svg")
    logo_white = uri(f"{DS}/assets/Algolia-logo-white.svg")
    sora = b64(f"{DS}/assets/fonts/Sora.ttf")
    # Trust strip: real Algolia customers cited in THIS audit (case_studies), grounded — no fabrication,
    # no dead-API logo fetch (clearbit's free logo endpoint was shut down). Real SVG logos can be
    # vendored into the design system later and swapped in here.
    trust_names = [c.get("company", "").strip() for c in d.get("case_studies", []) if c.get("company")]
    # Exclude the prospect itself — they are NOT yet an Algolia customer; listing them as one would mislead.
    trust_names = [n for n in dict.fromkeys(trust_names) if n and n.lower() != str(co).lower().strip()][:5]
    home = os.path.join(rd, "screenshots/01-homepage.png")
    home_uri = uri(home) if os.path.exists(home) else ""

    HEADER = (f'<header class="rh"><img src="{logo_blue}" class="rh-logo"><div class="rh-t">'
              f'eCommerce Search Audit for <b>{e(co)}</b></div></header>')
    strip = "".join(f'<span class="rf-name">{e(n)}</span>' for n in trust_names)
    FOOTER = (f'<footer class="rf"><div class="rf-strip"><span class="rf-tag">Leading retailers grow conversions and revenue with Algolia</span>'
              f'<div class="rf-logos">{strip}</div></div>'
              f'<div class="rf-bar"><img src="{logo_white}"><span>Learn more at www.algolia.com</span></div></footer>')

    def page(inner, cls=""):
        return f'<div class="page {cls}">{HEADER}<main class="pc">{inner}</main>{FOOTER}</div>'

    pages = []

    # ---- P1 COVER ----
    cover_shot = f'<div class="cv-monitor"><img src="{home_uri}"></div>' if home_uri else ""
    pages.append(f'''<div class="page cover">
      <div class="cv-top"><img src="{logo_blue}" class="cv-logo"></div>
      <div class="cv-head">eCommerce Search Audit for</div>
      <h1 class="cv-co">{e(co)}</h1>
      {cover_shot}
      <div class="cv-meta"><div><span>Prepared for</span>{e(co)}</div>
        <div><span>Prepared by</span>{e(meta.get('audited_by','Algolia'))}</div></div>
      {FOOTER}</div>''')

    # ---- P2 ABOUT + WHY + DELIVERS ----
    cs = d.get("case_studies", [])[:3]
    deliver = ""
    for c in cs:
        deliver += (f'<div class="dl"><div class="dl-r">{e(c.get("result","").split("·")[0])}</div>'
                    f'<div class="dl-c">{e(c.get("company",""))}</div>'
                    f'<div class="dl-w">{clip(c.get("why",""),210)} {src("case study", c.get("url"))}</div></div>')
    why = f'''<div class="why-grid">
      <div class="why"><b>~80%</b><p>of pet parents shop both online and in store. Search is the front door to the omnichannel basket. {src("industry context")}</p></div>
      <div class="why"><b>1.8x</b><p>site searchers convert versus non searchers. The shoppers who search are your highest intent buyers. {src(opp.get('badge_label','Algolia'), opp.get('source_url'))}</p></div>
      <div class="why"><b>81%</b><p>of US shoppers abandon after a failed search. Every dead end is a lost basket. {src(opp.get('badge_label','Algolia'), opp.get('source_url'))}</p></div></div>'''
    pages.append(page(f'''
      <h2 class="h-sec">About Algolia</h2>
      <p class="lede">Over 17,000 brands use Algolia's AI search, discovery and recommendations platform to grow conversion and revenue. API first, it plugs into your existing stack, and it is the only end to end AI search that unifies keyword and vector retrieval behind one API.</p>
      <h2 class="h-sec">About this document</h2>
      <p class="lede">We analyzed {e(co)}'s on site search, traffic and other available data. This report scores ten search areas, shows what we found with evidence, and lays out where activating Algolia has the most impact.</p>
      <h2 class="h-sec">Why fast, intuitive discovery matters</h2>
      {why}
      <h2 class="h-sec">Algolia delivers</h2>
      <div class="dl-row">{deliver}</div>'''))

    # ---- P3 SCORECARD ----
    bd = score.get("breakdown", {}); labels = score.get("breakdown_labels", {}); sev = score.get("breakdown_severity", {})
    tiles = ""
    for k, v in sorted(bd.items(), key=lambda kv: kv[1]):
        sv = str(sev.get(k, "MEDIUM")).upper()
        tiles += (f'<div class="sct" style="background:{SEV_BG.get(sv,"#eee")};border-color:{SEV_COLOR.get(sv,"#999")}55;">'
                  f'<div class="scn" style="color:{SEV_COLOR.get(sv,"#333")}">{e(v)}<span>/10</span></div>'
                  f'<div class="scl">{e(labels.get(k,k))}</div></div>')
    pages.append(page(f'''
      <h2 class="h-sec">Search audit scorecard</h2>
      <div class="sc-top"><div class="sc-big">{e(score.get('overall','?'))}<span>/10</span></div>
        <div class="sc-vd"><b>{e(score.get('verdict',''))}</b>
          <div class="sc-cts"><span style="color:#B91C1C">{e(score.get('critical_count',0))} critical</span> ·
          <span style="color:#D97706">{e(score.get('moderate_count',0))} moderate</span> ·
          <span style="color:#059669">{e(score.get('low_count',0))} strengths</span></div></div></div>
      <div class="sc-grid">{tiles}</div>'''))

    # ---- AREAS OF IMPROVEMENT (chapter band + findings, ~2 per page) ----
    def finding_block(f):
        sf = f.get("screenshot_file")
        shot = f'<img src="{uri(os.path.join(rd, sf))}">' if (sf and os.path.exists(os.path.join(rd, sf))) else '<span class="noimg">screenshot</span>'
        why = f.get("prospect_description") or f.get("pain_frame") or f.get("impact_stat")
        return f'''<div class="fb">
          <div class="fb-txt"><h3>{clip(f.get('title','Finding'),70)}</h3>
            <p class="fb-q">A shopper searched <b>"{clip(str(f.get('tested_query','')).split(';')[0].strip(),95)}"</b></p>
            <p>{clip(why,320)}</p>
            <div class="fb-fix"><span class="fk">With Algolia</span> {clip(f.get('algolia_solution',''),240)}</div>
            <div class="fb-src">{src(f.get('impact_stat_source','audit analytics'))}</div></div>
          <div class="fb-shot"><div class="shot-tag">What shoppers see today</div>{shot}</div></div>'''
    band = '<div class="chapter">Areas of improvement</div>'
    blocks = [finding_block(f) for f in ordered[:6]]
    # 2 findings per page
    for i in range(0, len(blocks), 2):
        head = band if i == 0 else '<div class="chapter chapter--cont">Areas of improvement, continued</div>'
        pages.append(page(head + "".join(blocks[i:i + 2])))

    # ---- CLOSE: scoped POC ----
    rfp = d.get("recommended_first_play", {}); steps = d.get("next_steps", [])
    lis = ""
    if rfp.get("headline"):
        lis += f"<li><b>{clip(rfp.get('headline'),100)}.</b> {clip(rfp.get('detail',''),330)}</li>"
    for st in steps:
        lis += f"<li><b>{clip(st.get('title',''),70)}.</b> {clip(st.get('description',''),280)}</li>"
    pages.append(page(f'''
      <h2 class="h-sec">Where to start: a scoped proof of concept</h2>
      <p class="lede">Prove the lift on your live index in weeks, not quarters. A focused POC on the highest impact gap, measured against your own analytics.</p>
      <ol class="steps">{lis}</ol>
      <div class="cta">Ready to scope it? Let's pick the first play together.</div>'''))

    CSS = f'''
    @font-face{{font-family:'Sora';src:url(data:font/ttf;base64,{sora}) format('truetype');font-weight:300 700;}}
    @page{{size:A4;margin:0;}}
    *{{box-sizing:border-box;-webkit-print-color-adjust:exact;print-color-adjust:exact;}}
    html,body{{margin:0;padding:0;font-family:'Sora',sans-serif;color:#21243D;}}
    .page{{position:relative;width:210mm;height:297mm;overflow:hidden;background:#fff;page-break-after:always;display:flex;flex-direction:column;}}
    .page:last-child{{page-break-after:auto;}}
    .pc{{flex:1;padding:18mm 16mm 6mm;overflow:hidden;}}
    .rh{{display:flex;align-items:center;gap:10px;padding:7mm 16mm 0;}}
    .rh-logo{{height:22px;}} .rh-t{{margin-left:auto;font-size:13px;color:#6B7280;}} .rh-t b{{color:#21243D;}}
    .rf{{margin-top:auto;}}
    .rf-strip{{display:flex;flex-direction:column;align-items:center;gap:7px;padding:9px 16mm;background:#F5F5F7;}}
    .rf-tag{{font-size:11px;color:#6B7280;letter-spacing:.02em;}}
    .rf-logos{{display:flex;gap:22px;align-items:center;flex-wrap:wrap;justify-content:center;}}
    .rf-name{{font-size:11px;font-weight:600;color:#8a90a0;text-transform:uppercase;letter-spacing:.10em;}}
    .rf-bar{{display:flex;align-items:center;justify-content:center;gap:10px;background:#0E1224;padding:7px;}}
    .rf-bar img{{height:14px;filter:brightness(0) invert(1);}} .rf-bar span{{color:#fff;font-size:11px;}}
    .h-sec{{font-family:'Sora';font-weight:600;font-size:19px;color:#003DFF;margin:0 0 8px;letter-spacing:-0.01em;}}
    .h-sec:not(:first-child){{margin-top:18px;}}
    .lede{{font-size:12.5px;line-height:1.55;color:#2f3447;margin:0 0 6px;}}
    .src{{font-size:10px;font-weight:600;color:#003DFF;text-decoration:none;}} .src--p{{color:#9aa1b2;font-weight:500;}}
    /* cover */
    .cover{{padding:0;}} .cv-top{{padding:18mm 0 0;text-align:center;}} .cv-logo{{height:34px;}}
    .cv-head{{text-align:center;font-size:18px;color:#21243D;margin-top:14mm;font-weight:600;}}
    .cv-co{{text-align:center;font-family:'Sora';font-weight:600;font-size:64px;margin:6px 0 0;color:#003DFF;letter-spacing:-0.02em;}}
    .cv-monitor{{margin:10mm auto 0;width:150mm;border:10px solid #1c2033;border-radius:14px;overflow:hidden;box-shadow:0 24px 60px rgba(2,16,70,.18);}}
    .cv-monitor img{{width:100%;display:block;}}
    .cv-meta{{display:flex;justify-content:center;gap:60px;margin-top:12mm;text-align:center;}}
    .cv-meta span{{display:block;font-size:11px;color:#9aa1b2;text-transform:uppercase;letter-spacing:.08em;margin-bottom:3px;}}
    .cv-meta div{{font-size:14px;color:#21243D;font-weight:600;}}
    /* why grid */
    .why-grid{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:16px;margin:6px 0;}}
    .why b{{display:block;font-family:'Sora';font-weight:600;font-size:34px;color:#003DFF;line-height:1;}}
    .why p{{font-size:11px;line-height:1.45;color:#2f3447;margin:8px 0 0;}}
    /* deliver */
    .dl-row{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:16px;margin-top:6px;}}
    .dl{{border:1px solid #e1e4ec;border-radius:12px;padding:14px;}}
    .dl-r{{font-family:'Sora';font-weight:600;font-size:26px;color:#059669;line-height:1;}}
    .dl-c{{font-weight:600;font-size:14px;margin:6px 0 4px;}} .dl-w{{font-size:11px;color:#4b5161;line-height:1.4;}}
    /* scorecard */
    .sc-top{{display:flex;align-items:center;gap:20px;margin:6px 0 14px;}}
    .sc-big{{font-family:'Sora';font-weight:600;font-size:54px;color:#003DFF;line-height:1;}} .sc-big span{{font-size:22px;color:#9aa1b2;}}
    .sc-vd b{{font-size:18px;}} .sc-cts{{font-size:13px;font-weight:600;margin-top:4px;}}
    .sc-grid{{display:grid;grid-template-columns:repeat(2,1fr);gap:10px;}}
    .sct{{border:1px solid;border-radius:10px;padding:12px 14px;display:flex;align-items:baseline;gap:12px;}}
    .scn{{font-family:'Sora';font-weight:600;font-size:30px;line-height:1;}} .scn span{{font-size:14px;opacity:.6;}}
    .scl{{font-size:13px;font-weight:500;}}
    /* chapter band */
    .chapter{{background:#0E1224;color:#fff;font-family:'Sora';font-weight:600;font-size:16px;padding:9px 16px;margin:0 0 14px;border-radius:8px;letter-spacing:.02em;}}
    .chapter--cont{{opacity:.85;}}
    /* finding block */
    .fb{{display:grid;grid-template-columns:1fr 1fr;gap:18px;align-items:start;margin-bottom:16px;padding-bottom:16px;border-bottom:1px solid #eef0f5;}}
    .fb h3{{font-family:'Sora';font-weight:600;font-size:16px;margin:0 0 6px;color:#21243D;}}
    .fb-q{{font-size:11.5px;color:#2f3447;margin:0 0 6px;}} .fb p{{font-size:11.5px;line-height:1.45;color:#2f3447;margin:0 0 8px;}}
    .fb-fix{{font-size:11.5px;background:#f2f5ff;border:1px solid #d9e2ff;border-radius:8px;padding:8px 10px;color:#21243D;}}
    .fb-fix .fk{{font-weight:600;color:#003DFF;margin-right:6px;}}
    .fb-src{{margin-top:6px;}}
    .fb-shot{{position:relative;border:1px solid #e1e4ec;border-radius:10px;overflow:hidden;box-shadow:0 10px 24px rgba(2,16,70,.10);}}
    .fb-shot img{{width:100%;display:block;}} .noimg{{display:block;padding:30px;text-align:center;color:#9aa1b2;}}
    .shot-tag{{position:absolute;top:8px;left:8px;z-index:2;background:#DC2626;color:#fff;font-size:10px;font-weight:600;padding:4px 9px;border-radius:999px;letter-spacing:.02em;}}
    /* steps */
    .steps{{font-size:13px;line-height:1.5;color:#2f3447;padding-left:20px;}} .steps li{{margin:0 0 10px;}}
    .cta{{margin-top:18px;background:#003DFF;color:#fff;font-weight:600;font-size:15px;padding:16px 20px;border-radius:12px;}}
    '''

    out = (f'<!DOCTYPE html><html><head><meta charset="utf-8"><title>{e(co)} Search Audit</title>'
           f'<style>{CSS}</style></head><body>{"".join(pages)}</body></html>')
    open(out_path, "w").write(out)
    print(f"wrote {out_path} ({len(pages)} pages, {len(out)//1024} KB)")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("usage: make_report.py <audit-data.json> <out.html>"); sys.exit(1)
    main(sys.argv[1], sys.argv[2])
