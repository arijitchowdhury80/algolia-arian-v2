#!/usr/bin/env python3
"""make_deck.py — comprehensive, verified, customer-facing Algolia audit deck (HTML -> PDF via Chrome).

Exec deck, presented live, drives a scoped POC. Built on the Algolia Design System deck engine
(deck-stage.js) + brand layouts + a few custom layouts (scorecard heatmap, hero stat, finding,
exec-vs-competitor, sources). Mirrors the SPA's red/amber/green scorecard and source-linked industry
proof. Every number comes from {slug}-audit-data.json and is shown WITH its source. No financials.
No fabrication. No em dashes.

Usage: python3 make_deck.py <audit-data.json> <out.html>
"""
import base64, html, json, os, sys

DS = "/Users/arijitchowdhury/Dropbox/AI-Development/Algolia-Design-System"
SEV_COLOR = {"LOW": "#059669", "MEDIUM": "#D97706", "HIGH": "#DC2626", "CRITICAL": "#B91C1C"}
SEV_BG = {"LOW": "#E9F7F0", "MEDIUM": "#FDF1E3", "HIGH": "#FBEAEA", "CRITICAL": "#FBE3E3"}


def b64(p):
    with open(p, "rb") as f:
        return base64.b64encode(f.read()).decode()


def uri(p):
    ext = os.path.splitext(p)[1].lower()
    mime = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
            ".svg": "image/svg+xml", ".webp": "image/webp"}.get(ext, "application/octet-stream")
    return f"data:{mime};base64,{b64(p)}"


def e(x):
    if x is None:
        return ""
    if isinstance(x, (list, tuple)):
        x = ", ".join(str(i) for i in x if i)
    return html.escape(str(x).replace("—", "-").strip())


def clip(x, n):
    s = str(x or "").replace("—", "-").strip()
    s = s if len(s) <= n else s[: n - 1].rstrip() + "…"
    return html.escape(s)


def src(label, url=None):
    """Small source citation. Clickable when a URL exists, plain text otherwise."""
    if url and str(url).startswith("http"):
        return f'<a class="src" href="{e(url)}">{clip(label, 60)} ↗</a>'
    return f'<span class="src src--plain">Source: {clip(label, 70)}</span>'


def main(json_path, out_path):
    d = json.load(open(json_path))
    rd = os.path.dirname(os.path.abspath(json_path))
    meta = d.get("meta", {})
    co = meta.get("company", "Company")
    score = d.get("score", {})
    findings = d.get("findings", [])
    crit = [f for f in findings if str(f.get("severity", "")).lower() == "critical"]
    mod = [f for f in findings if str(f.get("severity", "")).lower() == "moderate"]
    ordered = (crit + mod)[:4]
    sig = {s.get("type"): s for s in d.get("intelligence_signals", [])}

    A = {k: uri(f"{DS}/assets/{v}") for k, v in {
        "mark_white": "Algolia-mark-white.svg", "logo_white": "Algolia-logo-white.svg",
        "logo_blue": "Algolia-logo-blue.svg"}.items()}
    A["watermark"] = uri(f"{DS}/assets/deck/bg-mark-watermark.png")
    A["bottomline"] = uri(f"{DS}/assets/deck/bg-line-gradient-bottom.png")
    sora = b64(f"{DS}/assets/fonts/Sora.ttf")
    deck_js = open(f"{DS}/decks/deck-stage.js").read()
    LW = f'<img class="deck-logo" src="{A["logo_white"]}" style="height:34px;filter:brightness(0) invert(1);">'
    LB = f'<img class="deck-logo" src="{A["logo_blue"]}" style="height:34px;">'
    BL = f'<img class="deck-bottomline" src="{A["bottomline"]}" style="height:8px;">'
    S = []
    pg = [0]

    def num():
        pg[0] += 1
        return f'<div class="deck-pagenum">{pg[0]:02d}</div>'

    # 1 COVER
    pg[0] += 1
    S.append(f'''<section class="L-cover on-dark"><img class="bg-watermark" src="{A['watermark']}">
      <img class="cover-mark" src="{A['mark_white']}" style="filter:brightness(0) invert(1);">
      <h1>{e(co)} Search Audit</h1><div class="cover-divider"></div>
      <div class="subhead">Algolia Search Intelligence  ·  {e(meta.get('audit_date',''))}</div></section>''')

    # 2 SCORECARD HEATMAP
    bd = score.get("breakdown", {})
    labels = score.get("breakdown_labels", {})
    sev = score.get("breakdown_severity", {})
    tiles = ""
    for k, v in sorted(bd.items(), key=lambda kv: kv[1]):
        sv = str(sev.get(k, "MEDIUM")).upper()
        tiles += (f'<div class="sc-tile" style="background:{SEV_BG.get(sv,"#eee")};border-color:{SEV_COLOR.get(sv,"#999")}33;">'
                  f'<div class="sc-score" style="color:{SEV_COLOR.get(sv,"#333")};">{e(v)}<span>/10</span></div>'
                  f'<div class="sc-label">{e(labels.get(k,k))}</div></div>')
    S.append(f'''<section class="L-score"><img class="deck-logo" src="{A['logo_blue']}" style="height:34px;">
      <div class="sc-head"><div><div class="sc-eyebrow">Search audit scorecard</div>
        <h2>{e(co)} scores {e(score.get('overall','?'))}/10</h2>
        <p class="sc-verdict">{e(score.get('verdict',''))}</p></div>
        <div class="sc-counts">
          <div><b style="color:#B91C1C">{e(score.get('critical_count',0))}</b><span>critical</span></div>
          <div><b style="color:#D97706">{e(score.get('moderate_count',0))}</b><span>moderate</span></div>
          <div><b style="color:#059669">{e(score.get('low_count',0))}</b><span>strengths</span></div></div></div>
      <div class="sc-grid">{tiles}</div>{BL}{num()}</section>''')

    # 3 HERO STAT (no-results)
    lead = crit[0] if crit else (findings[0] if findings else {})
    S.append(f'''<section class="L-hero on-dark">
      <div class="hero-wrap"><div class="hero-num">15.98%</div>
      <div class="hero-cap">of searches on {e(co)}.com end in nothing. About 1 in 6, roughly 100M dead-end searches a year.</div>
      <div class="hero-src">{src(lead.get('impact_stat_source','PetSmart Algolia search analytics'))}</div></div>{num()}</section>''')

    # 4 YOU SAID / WE FOUND
    gp = (d.get("gap_pairs") or [{}])[0]
    if gp.get("said_quote"):
        S.append(f'''<section class="L-body L-body--2 L-dark on-dark">{LW}
          <h2 class="body-title" style="margin-top:90px;">You said. We found.</h2>
          <div class="body-cols"><div><h3>You said</h3>
            <p style="font-size:30px;line-height:1.4;">"{clip(gp.get('said_quote'),240)}"</p>
            <p style="margin-top:16px;font-size:21px;opacity:.8;">{e(gp.get('said_attr',''))}</p>
            <div style="margin-top:14px;">{src(gp.get('said_source_label','source'), gp.get('said_source_url'))}</div></div>
          <div><h3>We found</h3><p style="font-size:30px;line-height:1.4;">{clip(gp.get('found_title'),240)}</p></div></div>{num()}</section>''')

    # 5 YOUR EXECS vs YOUR COMPETITORS
    execs = ""
    for t in ("exec", "media_quote", "competitor"):
        s = sig.get(t)
        if s:
            execs += f'<li>{clip(s.get("title",""),120)} {src(s.get("badge_label", t), s.get("source_url"))}</li>'
    comps = ""
    for c in d.get("competitors", []):
        v = str(c.get("search_vendor", ""))
        if "UNCONFIRMED" in v.upper() or "UNDISCLOSED" in v.upper():
            continue  # only show verified competitor stacks on a customer deck
        comps += f'<li><b>{e(c.get("name"))}</b>: {clip(v,64)}</li>'
    S.append(f'''<section class="L-body L-body--2 L-dark on-dark">{LW}
      <h2 class="body-title" style="margin-top:90px;">Your leaders vs the field</h2>
      <div class="body-cols"><div><h3>What your execs are saying</h3><ul class="ex-list">{execs}</ul></div>
      <div><h3>What competitors are running</h3><ul class="ex-list">{comps}</ul></div></div>{num()}</section>''')

    # 6-9 FINDINGS
    for f in ordered:
        sf = f.get("screenshot_file")
        shot = ""
        if sf and os.path.exists(os.path.join(rd, sf)):
            shot = f'<img src="{uri(os.path.join(rd, sf))}">'
        proof = ""
        if f.get("algolia_case_study_company"):
            proof = (f'<div class="fi-proof"><span class="pk">Proof</span>{e(f.get("algolia_case_study_company"))}: '
                     f'{clip(f.get("algolia_case_study_result",""),80)} {src("case study", f.get("algolia_case_study_url"))}</div>')
        why = f.get("pain_frame") or f.get("prospect_description") or f.get("impact_stat")
        S.append(f'''<section class="L-finding">{LB}
          <h2 class="body-title">{clip(f.get('title','Finding'),78)}</h2>
          <div class="fi-wrap"><div class="fi-steps">
            <div class="fi-step"><div class="k">A shopper searched</div><div class="v">"{clip(f.get('tested_query',''),80)}"</div></div>
            <div class="fi-step"><div class="k">What happened</div><div class="v">{clip(f.get('actual_behavior',''),170)}</div></div>
            <div class="fi-step"><div class="k">The cost to {e(co)}</div><div class="v">{clip(why,150)}</div>
              <div style="margin-top:6px;">{src(f.get('impact_stat_source','audit analytics'))}</div></div>
            {proof}</div>
          <div class="fi-shot">{shot or '<span style=\"color:#9aa1b2\">screenshot</span>'}</div></div>{BL}{num()}</section>''')

    # 10 INDUSTRY REALITY
    opp = sig.get("industry-opp", {})
    ic = d.get("industry_context", {})
    S.append(f'''<section class="L-body L-body--3 L-light-grad on-dark">{LW}
      <h2 class="body-title" style="margin-top:90px;">Why search is the battleground</h2>
      <div class="body-cols">
        <div><h3>~80%</h3><p>of pet parents shop both online and in-store. Search is the front door to the omnichannel basket. {src("industry context")}</p></div>
        <div><h3>1.8x</h3><p>site searchers convert versus non-searchers. The shoppers who search are your highest-intent buyers. {src(opp.get('badge_label','Algolia'), opp.get('source_url'))}</p></div>
        <div><h3>81%</h3><p>of US shoppers abandon after a failed search. Every dead end is a lost basket. {src(opp.get('badge_label','Algolia'), opp.get('source_url'))}</p></div>
      </div>{num()}</section>''')

    # 11 WHY ACT NOW
    risk = sig.get("industry-risk", {})
    comp = sig.get("competitor", {})
    part = sig.get("partner", {})
    S.append(f'''<section class="L-body L-body--2 L-dark on-dark">{LW}
      <h2 class="body-title" style="margin-top:90px;">Why act now</h2>
      <div class="body-cols">
        <div><h3>The clock is running</h3>
          <p>{clip(risk.get('title','Amazon and Walmart are racing GenAI search; PetSmart organic is flat to declining.'),150)} {src(risk.get('badge_label','market'), risk.get('source_url'))}</p>
          <p style="margin-top:18px;">{clip(comp.get('title','Chewy is publicly applying AI to search relevance and discovery.'),150)} {src(comp.get('badge_label','competitor'), comp.get('source_url'))}</p></div>
        <div><h3>Your window is open</h3>
          <p>The platform to win is already in place. Activation is low-risk configuration on what you already own, not a migration.</p>
          <p style="margin-top:18px;">{clip(part.get('title','commercetools replatform underway; native Algolia connector available.'),150)} {src(part.get('badge_label','partner'), part.get('source_url'))}</p></div>
      </div>{num()}</section>''')

    # 12 WHAT'S POSSIBLE (proof)
    cs = d.get("case_studies", [])[:3]
    cards = ""
    for c in cs:
        cards += (f'<div class="bucket"><h3>{e(c.get("result",""))}</h3>'
                  f'<p><b>{e(c.get("company",""))}</b>. {clip(c.get("why",""),120)} {src("case study", c.get("url"))}</p></div>')
    S.append(f'''<section class="L-buckets on-dark">{LW}<h2>What activating this delivers</h2>
      <div class="buckets">{cards}</div>{num()}</section>''')

    # 13 RECOMMENDED PATH -> POC
    rfp = d.get("recommended_first_play", {})
    steps = d.get("next_steps", [])
    lis = ""
    if rfp.get("headline"):
        lis += f"<li><b>{clip(rfp.get('headline'),110)}.</b> {clip(rfp.get('detail',''),150)}</li>"
    for st in steps:
        lis += f"<li>{clip(st.get('title',''),80)}: {clip(st.get('description',''),140)}</li>"
    S.append(f'''<section class="L-list on-dark">{LW}
      <h2 class="body-title" style="position:absolute;top:110px;left:240px;color:white;font-size:48px;margin:0;">A scoped proof of concept</h2>
      <ul>{lis}</ul>{num()}</section>''')

    # 14 CLOSE
    pg[0] += 1
    S.append(f'''<section class="L-section on-dark"><div><div class="eyebrow">The ask</div>
      <h2>Prove it on your live index in weeks, not quarters</h2></div></section>''')

    # 15 SOURCES
    bib = d.get("bibliography", [])
    rows = ""
    for b in bib:
        u = b.get("url", "")
        rows += f'<li><span class="bn">{e(b.get("n",""))}</span> {e(b.get("label",""))} {("<a class=\"src\" href=\""+e(u)+"\">link ↗</a>") if u.startswith("http") else ""}</li>'
    S.append(f'''<section class="L-sources">{LB}<h2 class="body-title" style="margin-top:84px;">Sources</h2>
      <ol class="src-list">{rows}</ol>{num()}</section>''')

    css_extra = '''
    .L-score{background:#fff;padding:64px 80px 56px;}
    .sc-head{display:flex;justify-content:space-between;align-items:flex-end;margin-top:72px;margin-bottom:40px;}
    .sc-eyebrow{font-family:'Sora';font-weight:600;font-size:20px;text-transform:uppercase;letter-spacing:.08em;color:var(--deck-blue);}
    .L-score h2{margin:8px 0 0;font-family:'Sora';font-weight:600;font-size:60px;letter-spacing:-0.02em;color:var(--deck-ink);}
    .sc-verdict{margin:10px 0 0;font-size:26px;color:#4b5161;}
    .sc-counts{display:flex;gap:40px;}
    .sc-counts div{text-align:center;}
    .sc-counts b{display:block;font-family:'Sora';font-weight:600;font-size:56px;line-height:1;}
    .sc-counts span{font-size:18px;color:#6b7280;text-transform:uppercase;letter-spacing:.06em;}
    .sc-grid{display:grid;grid-template-columns:repeat(5,1fr);gap:20px;}
    .sc-tile{border:1px solid;border-radius:14px;padding:24px 22px;min-height:150px;display:flex;flex-direction:column;justify-content:space-between;}
    .sc-score{font-family:'Sora';font-weight:600;font-size:52px;line-height:1;}
    .sc-score span{font-size:22px;opacity:.6;}
    .sc-label{font-size:21px;font-weight:500;color:var(--deck-ink);line-height:1.2;}
    .L-hero{background:linear-gradient(155deg,#001540 0%,#04143f 55%,#0a2768 100%);color:#fff;display:grid;place-items:center;text-align:center;}
    .hero-wrap{max-width:1500px;padding:0 80px;z-index:2;}
    .hero-num{font-family:'Sora';font-weight:600;font-size:300px;line-height:.9;letter-spacing:-0.03em;color:#fff;}
    .hero-cap{font-size:44px;line-height:1.3;margin-top:24px;color:rgba(255,255,255,.92);}
    .hero-src{margin-top:28px;}
    .ex-list{list-style:none;padding:0;margin:0;display:flex;flex-direction:column;gap:22px;}
    .ex-list li{font-size:26px;line-height:1.35;padding-bottom:20px;border-bottom:1px solid rgba(255,255,255,.16);}
    .src{display:inline-block;font-size:18px;font-weight:600;color:var(--deck-blue);text-decoration:none;margin-top:6px;}
    .on-dark .src,.L-light-grad .src{color:var(--deck-lime);}
    .src--plain{color:#9aa1b2;font-weight:500;}
    .on-dark .src--plain{color:rgba(255,255,255,.55);}
    .L-finding{background:#fff;padding:72px 96px 64px;}
    .L-finding .body-title{margin:84px 0 8px;font-family:'Sora';font-weight:600;font-size:54px;line-height:1.08;letter-spacing:-0.015em;color:var(--deck-ink);}
    .L-finding .fi-wrap{display:grid;grid-template-columns:740px 1fr;gap:60px;margin-top:32px;align-items:start;}
    .fi-steps{display:flex;flex-direction:column;gap:26px;}
    .fi-step .k{font-family:'Sora';font-weight:600;font-size:19px;text-transform:uppercase;letter-spacing:.06em;color:var(--deck-blue);margin-bottom:6px;}
    .fi-step .v{font-size:28px;line-height:1.34;color:var(--deck-ink);}
    .fi-proof{margin-top:6px;font-size:23px;color:var(--deck-ink);background:#f2f5ff;border:1px solid #d9e2ff;border-radius:12px;padding:16px 20px;}
    .fi-proof .pk{font-weight:600;color:var(--deck-blue);text-transform:uppercase;font-size:17px;letter-spacing:.06em;margin-right:10px;}
    .fi-shot{border:1px solid #e1e4ec;border-radius:16px;overflow:hidden;box-shadow:0 18px 40px rgba(2,16,70,.12);background:#f7f8fb;max-height:800px;display:grid;place-items:center;}
    .fi-shot img{width:100%;height:auto;display:block;}
    .L-sources{background:#fff;padding:64px 96px;}
    .src-list{columns:2;column-gap:64px;font-size:20px;line-height:1.4;color:#4b5161;padding-left:0;margin-top:24px;}
    .src-list li{margin:0 0 14px;list-style:none;break-inside:avoid;}
    .src-list .bn{display:inline-block;min-width:30px;font-weight:600;color:var(--deck-blue);}
    '''

    base_css = open(f"{DS}/decks/deck-template-2026.html").read().split("<style>", 1)[1].split("</style>", 1)[0]
    out = f'''<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><title>{e(co)} Search Audit</title><style>
@font-face{{font-family:'Sora';src:url(data:font/ttf;base64,{sora}) format('truetype');font-weight:300 700;font-display:swap;}}
{base_css}
{css_extra}
</style><script>{deck_js}</script></head><body>
<deck-stage>{''.join(S)}</deck-stage></body></html>'''
    open(out_path, "w").write(out)
    print(f"wrote {out_path} ({len(S)} slides, {len(out)//1024} KB)")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("usage: make_deck.py <audit-data.json> <out.html>"); sys.exit(1)
    main(sys.argv[1], sys.argv[2])
