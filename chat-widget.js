/**
 * PRISM report-chat widget — drop-in for every published audit page.
 *
 * A floating "Ask about this audit" panel. Reads the company slug from the URL
 * (/<slug>/), streams grounded answers from /api/chat (→ Hermes-PRISM report-QA,
 * the same brain as the Telegram bot). Answers come ONLY from this company's audit;
 * anything not in the report is refused by the Hermes grounding gate.
 *
 * Renders Markdown (bold/italic/lists/headings/code/links) and auto-links mentions
 * of audit sections so a click scrolls to that section of the report.
 * Panel is fluid and has an expand toggle that uses the full viewport height.
 *
 * Include once per page:  <script src="/chat-widget.js" defer></script>
 */
(function () {
  "use strict";

  var slug = (location.pathname.split("/").filter(Boolean)[0] || "").toLowerCase();
  if (!slug || slug === "index.html") return;

  var sid;
  try {
    sid = localStorage.getItem("prism_sid");
    if (!sid) { sid = "v" + Math.random().toString(36).slice(2, 12); localStorage.setItem("prism_sid", sid); }
  } catch (e) { sid = "v" + Math.random().toString(36).slice(2, 12); }

  // --- styles (fluid panel + expand state + rendered-markdown typography) ---
  var css =
    ":root{--pc-w:440px}" +
    "#prism-chat-btn{position:fixed;bottom:24px;right:24px;z-index:99999;height:54px;padding:0 22px;border:0;border-radius:27px;background:#21243D;color:#fff;font-family:'Sora',sans-serif;font-size:15px;font-weight:600;cursor:pointer;box-shadow:0 8px 28px rgba(33,36,61,.32);display:flex;align-items:center;gap:9px}" +
    "#prism-chat-btn:hover{background:#2c3050}" +
    // Full-height side drawer. Slides from the edge, never floats over content. Width is a live CSS var so resize is fluid.
    "#prism-chat-panel{position:fixed;top:0;right:0;bottom:0;z-index:99999;width:var(--pc-w);max-width:100vw;background:#fff;box-shadow:-14px 0 50px rgba(33,36,61,.22);display:flex;flex-direction:column;overflow:hidden;font-family:'Sora',sans-serif;transform:translateX(101%);transition:transform .26s cubic-bezier(.2,.8,.2,1)}" +
    "#prism-chat-panel.pc-open{transform:none}" +
    "#prism-chat-panel.pc-left{left:0;right:auto;box-shadow:14px 0 50px rgba(33,36,61,.22);transform:translateX(-101%)}" +
    "#prism-chat-panel.pc-left.pc-open{transform:none}" +
    // drag handle on the inner edge → resize
    "#prism-chat-grip{position:absolute;top:0;left:0;width:8px;height:100%;cursor:ew-resize;background:transparent;z-index:6}" +
    "#prism-chat-grip:hover,#prism-chat-grip.pc-dragging{background:rgba(47,84,255,.25)}" +
    "#prism-chat-panel.pc-left #prism-chat-grip{left:auto;right:0}" +
    "#prism-chat-dock{background:0;border:0;color:rgba(255,255,255,.7);cursor:pointer;line-height:1;padding:4px;border-radius:6px;font-size:17px}" +
    "#prism-chat-dock:hover{background:rgba(255,255,255,.12);color:#fff}" +
    // Reflow the report so the drawer never covers it. The report column (#layout) is centered in the
    // body, so we pad the BODY by the drawer width — the column re-centers in the remaining space and
    // can never sit under the drawer. Follows the live width var. Right dock default; left when docked left.
    "@media(min-width:760px){" +
      "html.pc-chat-open body{padding-right:calc(var(--pc-w) + 28px)!important;transition:padding .26s ease}" +
      "html.pc-chat-open.pc-chat-left body{padding-right:0!important;padding-left:calc(var(--pc-w) + 28px)!important}" +
    "}" +
    "@media(max-width:759px){#prism-chat-panel{width:100vw}}" +
    "#prism-chat-head{background:#21243D;color:#fff;padding:16px 18px;display:flex;align-items:center;gap:10px;flex-shrink:0}" +
    "#prism-chat-head .t{font-size:15px;font-weight:600}#prism-chat-head .s{font-size:12px;color:rgba(255,255,255,.55);margin-top:2px}" +
    "#prism-chat-head .av{width:40px;height:40px;border-radius:50%;object-fit:cover;object-position:center top;flex-shrink:0;border:2px solid rgba(255,255,255,.25)}" +
    "#prism-chat-tools{margin-left:auto;display:flex;align-items:center;gap:6px}" +
    "#prism-chat-exp,#prism-chat-x{background:0;border:0;color:rgba(255,255,255,.7);cursor:pointer;line-height:1;padding:4px;border-radius:6px}" +
    "#prism-chat-exp{font-size:20px}#prism-chat-x{font-size:22px}" +
    "#prism-chat-exp:hover,#prism-chat-x:hover{background:rgba(255,255,255,.12);color:#fff}" +
    "#prism-chat-log{flex:1;overflow-y:auto;padding:18px;background:#F8F9FB;display:flex;flex-direction:column;gap:12px}" +
    ".pc-msg{max-width:88%;padding:11px 14px;border-radius:13px;font-size:14px;line-height:1.55;word-wrap:break-word;overflow-wrap:anywhere}" +
    ".pc-user{align-self:flex-end;background:#21243D;color:#fff;border-bottom-right-radius:4px;white-space:pre-wrap}" +
    ".pc-bot{align-self:flex-start;background:#fff;color:#23263B;border:1px solid #e7e9f0;border-bottom-left-radius:4px}" +
    ".pc-bot.err{color:#b4232a;border-color:#f3d0d2}" +
    ".pc-bot p{margin:0 0 8px}.pc-bot p:last-child{margin-bottom:0}" +
    ".pc-bot h3{font-size:14px;font-weight:700;margin:10px 0 5px}.pc-bot h4{font-size:13px;font-weight:700;margin:9px 0 4px;color:#3a3f5c}" +
    ".pc-bot ul,.pc-bot ol{margin:4px 0 8px;padding-left:20px}.pc-bot li{margin:2px 0}" +
    ".pc-bot a{color:#2f54ff;text-decoration:underline;text-underline-offset:2px}" +
    ".pc-bot a.pc-jump{color:#21243D;text-decoration-color:#9aa2c8;font-weight:600;cursor:pointer}.pc-bot a.pc-jump:hover{color:#2f54ff}" +
    ".pc-rel{margin-top:11px;padding-top:9px;border-top:1px solid #eceef4;display:flex;flex-wrap:wrap;gap:6px;align-items:center}" +
    ".pc-rel-l{font-size:10.5px;text-transform:uppercase;letter-spacing:.05em;color:#8a90ab;width:100%;margin-bottom:1px}" +
    ".pc-bot a.pc-chip{display:inline-block;background:#eef1fb;border:1px solid #dfe3f5;border-radius:999px;padding:3px 11px;font-size:12px;font-weight:600;color:#2f54ff!important;text-decoration:none!important}" +
    ".pc-bot a.pc-chip:hover{background:#2f54ff;color:#fff!important;border-color:#2f54ff}" +
    "@keyframes pcflash{0%{background:rgba(255,224,102,.55)}100%{background:transparent}}" +
    ".pc-flash{animation:pcflash 1.8s ease;border-radius:8px}" +
    ".pc-bot code{background:#eef0f6;border-radius:4px;padding:1px 5px;font-family:ui-monospace,Menlo,monospace;font-size:12.5px}" +
    ".pc-bot pre{background:#1f2233;color:#e8eaf6;border-radius:8px;padding:10px 12px;overflow-x:auto;margin:6px 0}.pc-bot pre code{background:0;color:inherit;padding:0}" +
    "#prism-chat-form{display:flex;gap:8px;padding:14px;border-top:1px solid #eceef4;background:#fff;flex-shrink:0}" +
    "#prism-chat-in{flex:1;border:1px solid #d7dae6;border-radius:10px;padding:10px 12px;font-family:inherit;font-size:14px;resize:none;outline:0;max-height:120px}" +
    "#prism-chat-in:focus{border-color:#21243D}" +
    "#prism-chat-send{border:0;border-radius:10px;background:#21243D;color:#fff;padding:0 16px;font-family:inherit;font-size:14px;font-weight:600;cursor:pointer}" +
    "#prism-chat-send:disabled{opacity:.5;cursor:default}";
  var style = document.createElement("style");
  style.textContent = css;
  document.head.appendChild(style);

  var company = slug.replace(/-/g, " ").replace(/\b\w/g, function (c) { return c.toUpperCase(); });
  var btn = el("button", { id: "prism-chat-btn" });
  btn.innerHTML = "<span>🔍</span> Ask about this audit";
  var panel = el("div", { id: "prism-chat-panel" });
  panel.innerHTML =
    '<div id="prism-chat-grip" title="Drag to resize"></div>' +
    '<div id="prism-chat-head"><img class="av" src="/assets/cassandra.png" alt="Cassandra" /><div><div class="t">Cassandra</div><div class="s">Grounded in the ' + escapeHtml(company) + " audit</div></div>" +
    '<div id="prism-chat-tools"><button id="prism-chat-dock" aria-label="dock side" title="Dock left/right">⇄</button><button id="prism-chat-exp" aria-label="expand" title="Expand">⤢</button><button id="prism-chat-x" aria-label="close" title="Close">×</button></div></div>' +
    '<div id="prism-chat-log"></div>' +
    '<form id="prism-chat-form"><textarea id="prism-chat-in" rows="1" placeholder="Ask anything about this audit…"></textarea><button id="prism-chat-send" type="submit">Send</button></form>';
  document.body.appendChild(btn);
  document.body.appendChild(panel);

  var log = panel.querySelector("#prism-chat-log");
  var form = panel.querySelector("#prism-chat-form");
  var input = panel.querySelector("#prism-chat-in");
  var send = panel.querySelector("#prism-chat-send");
  var expBtn = panel.querySelector("#prism-chat-exp");
  var dockBtn = panel.querySelector("#prism-chat-dock");
  var grip = panel.querySelector("#prism-chat-grip");
  var greeted = false, expanded = false, normalW = 440;

  var root = document.documentElement;

  function clampW(w) { return Math.max(320, Math.min(Math.round(window.innerWidth * 0.92), w)); }
  function setWidth(w, persist) {
    w = clampW(w);
    root.style.setProperty("--pc-w", w + "px");
    if (persist) { try { localStorage.setItem("prism_chat_w", String(w)); } catch (e) {} }
    return w;
  }

  // restore saved width + dock side
  try {
    var sw = parseInt(localStorage.getItem("prism_chat_w"), 10);
    if (sw) { normalW = clampW(sw); }
    if (localStorage.getItem("prism_chat_side") === "left") panel.classList.add("pc-left");
  } catch (e) {}
  setWidth(normalW, false);

  btn.onclick = function () {
    panel.classList.add("pc-open");
    root.classList.add("pc-chat-open");
    if (panel.classList.contains("pc-left")) root.classList.add("pc-chat-left");
    btn.style.display = "none"; input.focus();
    if (!greeted) { greeted = true; addMsg("bot", "Ask me anything about the " + company + " search audit — I answer only from the report."); }
  };
  panel.querySelector("#prism-chat-x").onclick = function () {
    panel.classList.remove("pc-open"); root.classList.remove("pc-chat-open", "pc-chat-left"); btn.style.display = "flex";
  };
  expBtn.onclick = function () {
    expanded = !expanded;
    if (expanded) { normalW = parseInt(getComputedStyle(root).getPropertyValue("--pc-w"), 10) || normalW; setWidth(Math.round(window.innerWidth * 0.9), false); }
    else { setWidth(normalW, true); }
    expBtn.textContent = expanded ? "⤡" : "⤢";
    expBtn.title = expanded ? "Restore" : "Expand";
    log.scrollTop = log.scrollHeight;
  };
  dockBtn.onclick = function () {
    var left = panel.classList.toggle("pc-left");
    root.classList.toggle("pc-chat-left", left && panel.classList.contains("pc-open"));
    try { localStorage.setItem("prism_chat_side", left ? "left" : "right"); } catch (e) {}
  };

  // drag-to-resize via the inner-edge grip; content reflow follows the live width var
  grip.addEventListener("pointerdown", function (e) {
    e.preventDefault();
    var left = panel.classList.contains("pc-left");
    grip.classList.add("pc-dragging");
    try { grip.setPointerCapture(e.pointerId); } catch (_) {}
    function move(ev) {
      var w = left ? ev.clientX : (window.innerWidth - ev.clientX);
      setWidth(w, false);
      expanded = false; expBtn.textContent = "⤢"; expBtn.title = "Expand";
    }
    function up() {
      grip.classList.remove("pc-dragging");
      normalW = parseInt(getComputedStyle(root).getPropertyValue("--pc-w"), 10) || normalW;
      setWidth(normalW, true);
      document.removeEventListener("pointermove", move);
      document.removeEventListener("pointerup", up);
    }
    document.addEventListener("pointermove", move);
    document.addEventListener("pointerup", up);
  });

  input.addEventListener("keydown", function (e) {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); form.requestSubmit(); }
  });
  form.addEventListener("submit", function (e) {
    e.preventDefault();
    var text = input.value.trim();
    if (!text) return;
    input.value = ""; addMsg("user", text); ask(text);
  });

  // in-page section jumps (event delegation). Tab-aware: report content is split across tabs
  // (#tab-rail [data-tab] ↔ .section-group[data-tab]); a target in a hidden tab needs the tab
  // activated first, then we scroll + flash it so the user sees where they landed.
  log.addEventListener("click", function (e) {
    var a = e.target.closest && e.target.closest("a.pc-jump");
    if (!a) return;
    var id = a.getAttribute("href").slice(1);
    var t = document.getElementById(id);
    if (!t) return;
    e.preventDefault();
    var grp = t.closest && t.closest(".section-group");
    if (grp && getComputedStyle(grp).display === "none") {
      var tab = grp.getAttribute("data-tab");
      var tabBtn = tab && document.querySelector('#tab-rail [data-tab="' + tab + '"]');
      if (tabBtn) tabBtn.click();
    }
    setTimeout(function () {
      var el2 = document.getElementById(id);
      if (!el2) return;
      el2.scrollIntoView({ behavior: "smooth", block: "start" });
      el2.classList.remove("pc-flash"); void el2.offsetWidth; el2.classList.add("pc-flash");
    }, 70);
  });

  async function ask(text) {
    send.disabled = true;
    var bot = addMsg("bot", "");
    bot.innerHTML = "<p>…</p>";
    try {
      var res = await fetch("/api/chat", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text, slug: slug, sid: sid }),
      });
      if (!res.ok || !res.body) { bot.textContent = "Sorry — the audit chat is unavailable right now."; bot.classList.add("err"); return; }
      var reader = res.body.getReader(), dec = new TextDecoder(), acc = "";
      for (;;) {
        var r = await reader.read();
        if (r.done) break;
        acc += dec.decode(r.value, { stream: true });
        bot.innerHTML = mdToHtml(acc);
        log.scrollTop = log.scrollHeight;
      }
      if (!acc.trim()) { bot.innerHTML = "<p>(no response)</p>"; }
      else { bot.innerHTML = mdToHtml(acc); linkSections(bot); appendRelated(bot, acc); }
    } catch (err) {
      bot.textContent = "Connection error. Please try again."; bot.classList.add("err");
    } finally {
      send.disabled = false; input.focus(); log.scrollTop = log.scrollHeight;
    }
  }

  function addMsg(role, text) {
    var m = el("div", { class: "pc-msg " + (role === "user" ? "pc-user" : "pc-bot") });
    if (role === "user") m.textContent = text; else m.innerHTML = mdToHtml(text);
    log.appendChild(m); log.scrollTop = log.scrollHeight;
    return m;
  }

  // --- minimal, safe Markdown renderer (escape first, then format) ---
  function mdToHtml(src) {
    if (!src) return "";
    var s = escapeHtml(src);
    // Strip internal grounding markers that must never reach the reader:
    // [FACT], [ESTIMATE], and source-path citations like [FACT: strategic_angles.0.pain_points.0].
    // (The grounding discipline stays server-side; only the literal tag is removed from display.)
    s = s.replace(/[ \t]*\[(?:FACT|ESTIMATE)\b[^\]]*\]/gi, "");
    s = s.replace(/```([\s\S]*?)```/g, function (_, c) { return "<pre><code>" + c.replace(/^\n/, "") + "</code></pre>"; });
    s = s.replace(/`([^`]+)`/g, "<code>$1</code>");
    s = s.replace(/^###\s+(.*)$/gm, "<h4>$1</h4>").replace(/^##\s+(.*)$/gm, "<h3>$1</h3>").replace(/^#\s+(.*)$/gm, "<h3>$1</h3>");
    s = s.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>").replace(/(^|[^*])\*([^*\n]+)\*/g, "$1<em>$2</em>");
    s = s.replace(/\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');
    // Canonical contract: Cassandra emits BARE urls (not [text](url)) so they render identically on
    // Telegram (native autolink) and SPA. Autolink bare urls here; preceding char guard skips urls
    // already inside an href="..." from the rule above. Trailing punctuation is kept outside the link.
    s = s.replace(/(^|[\s(])(https?:\/\/[^\s<]+)/g, function (_, pre, url) {
      var trail = "", m = url.match(/[.,;:!?)\]]+$/);
      if (m) { trail = m[0]; url = url.slice(0, -trail.length); }
      return pre + '<a href="' + url + '" target="_blank" rel="noopener">' + url + '</a>' + trail;
    });
    s = s.replace(/(^|\n)((?:[-*]\s+.*(?:\n|$))+)/g, function (_, pre, blk) {
      var items = blk.trim().split("\n").map(function (li) { return "<li>" + li.replace(/^[-*]\s+/, "") + "</li>"; }).join("");
      return pre + "<ul>" + items + "</ul>";
    });
    s = s.replace(/(^|\n)((?:\d+\.\s+.*(?:\n|$))+)/g, function (_, pre, blk) {
      var items = blk.trim().split("\n").map(function (li) { return "<li>" + li.replace(/^\d+\.\s+/, "") + "</li>"; }).join("");
      return pre + "<ol>" + items + "</ol>";
    });
    s = s.replace(/\n{2,}/g, "</p><p>").replace(/\n/g, "<br>");
    return "<p>" + s + "</p>";
  }

  // --- auto-link mentions of audit sections → in-page anchors (only sections present on this page) ---
  var SECTION_KEYWORDS = [
    ["section-financials", /\b(financials?|revenue|ebitda|margin|conversion rate|conversion|aov|average order|basket size|sales)\b/i],
    ["section-techstack", /\b(tech stack|technology stack|search vendor|search platform|search engine|neuralsearch|current vendor|the platform|ibm|wcs|elastic|coveo|constructor|algolia)\b/i],
    ["section-traffic", /\b(traffic|engagement|bounce rate|visits?|annual visits|audience|sessions)\b/i],
    ["section-competitive", /\b(competitors?|competitive landscape|competition|rival|leroy merlin|adeo|chewy|amazon)\b/i],
    ["section-hiring", /\b(hiring|open roles?|job postings?|headcount|recruiting)\b/i],
    ["section-roi", /\b(roi|return on investment|business case|uplift|lost revenue|revenue opportunity|payback)\b/i],
    ["section-industry-context", /\b(industry context|industry benchmarks?|benchmark|vertical)\b/i],
    ["section-partner", /\b(partners?|co-sell|ecosystem)\b/i],
    ["section-quotes", /\b(executive quotes?|earnings call|quote)\b/i],
    ["section-case-studies", /\b(case stud(?:y|ies)|customer story|big w|decathlon|customers?)\b/i],
    ["section-signals", /\b(signals?|priorities|mandate|initiative|hot sale|cto|cio|ceo|cfo|leadership|new leaders?|executives?|c-suite|president)\b/i],
    ["section-discovery", /\b(discovery questions?|discovery)\b/i],
    ["section-outreach", /\b(outreach|email sequence|campaign|cold email)\b/i],
  ];
  var SECTION_LABEL = {
    "section-financials": "Financials", "section-techstack": "Tech Stack", "section-traffic": "Traffic",
    "section-competitive": "Competitors", "section-hiring": "Hiring", "section-roi": "Business Case",
    "section-industry-context": "Industry", "section-partner": "Partners", "section-quotes": "Exec Quotes",
    "section-case-studies": "Case Studies", "section-signals": "Signals", "section-discovery": "Discovery",
    "section-outreach": "Outreach",
  };
  // Reliable clickable navigation: append a "Jump to in the report" chip row with the sections the
  // answer actually touches (and that exist on this page). Each chip is a pc-jump so the delegated
  // click handler scrolls to it. This guarantees clickable sections even when inline matching misses.
  function appendRelated(container, text) {
    var done = {}, html = [];
    SECTION_KEYWORDS.forEach(function (k) {
      if (done[k[0]] || !document.getElementById(k[0]) || !k[1].test(text)) return;
      done[k[0]] = 1;
      html.push('<a class="pc-jump pc-chip" href="#' + k[0] + '">' + (SECTION_LABEL[k[0]] || k[0]) + " →</a>");
    });
    if (!html.length) return;
    var row = document.createElement("div");
    row.className = "pc-rel";
    row.innerHTML = '<span class="pc-rel-l">Jump to in the report</span>' + html.join("");
    container.appendChild(row);
  }
  function linkSections(container) {
    var avail = SECTION_KEYWORDS.filter(function (k) { return document.getElementById(k[0]); });
    if (!avail.length) return;
    var walker = document.createTreeWalker(container, NodeFilter.SHOW_TEXT, null);
    var nodes = [], n;
    while ((n = walker.nextNode())) { if (n.parentNode.closest("a")) continue; nodes.push(n); }
    var used = {};
    nodes.forEach(function (node) {
      for (var i = 0; i < avail.length; i++) {
        var id = avail[i][0], re = avail[i][1];
        if (used[id]) continue;
        var m = node.nodeValue.match(re);
        if (!m) continue;
        var idx = node.nodeValue.toLowerCase().indexOf(m[0].toLowerCase());
        var matched = node.splitText(idx);
        matched.splitText(m[0].length);
        var a = document.createElement("a");
        a.className = "pc-jump"; a.href = "#" + id; a.textContent = matched.nodeValue;
        matched.parentNode.replaceChild(a, matched);
        used[id] = true;
        return; // one link per text node keeps it readable
      }
    });
  }

  function el(tag, attrs) {
    var n = document.createElement(tag);
    for (var k in attrs) n.setAttribute(k, attrs[k]);
    return n;
  }
  function escapeHtml(s) {
    return String(s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; });
  }
})();
