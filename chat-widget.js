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
    "#prism-chat-btn{position:fixed;bottom:24px;right:24px;z-index:99999;height:54px;padding:0 22px;border:0;border-radius:27px;background:#21243D;color:#fff;font-family:'Sora',sans-serif;font-size:15px;font-weight:600;cursor:pointer;box-shadow:0 8px 28px rgba(33,36,61,.32);display:flex;align-items:center;gap:9px}" +
    "#prism-chat-btn:hover{background:#2c3050}" +
    "#prism-chat-panel{position:fixed;bottom:24px;right:24px;z-index:99999;width:clamp(320px,30vw,420px);height:min(620px,calc(100vh - 48px));max-width:calc(100vw - 32px);background:#fff;border-radius:16px;box-shadow:0 24px 64px rgba(33,36,61,.30);display:none;flex-direction:column;overflow:hidden;font-family:'Sora',sans-serif;transition:width .18s ease,height .18s ease}" +
    "#prism-chat-panel.pc-max{top:16px;bottom:16px;right:16px;height:auto;width:clamp(360px,42vw,640px)}" +
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
    '<div id="prism-chat-head"><img class="av" src="/assets/cassandra.png" alt="Cassandra" /><div><div class="t">Cassandra</div><div class="s">Grounded in the ' + escapeHtml(company) + " audit</div></div>" +
    '<div id="prism-chat-tools"><button id="prism-chat-exp" aria-label="expand" title="Expand">⤢</button><button id="prism-chat-x" aria-label="close" title="Close">×</button></div></div>' +
    '<div id="prism-chat-log"></div>' +
    '<form id="prism-chat-form"><textarea id="prism-chat-in" rows="1" placeholder="Ask anything about this audit…"></textarea><button id="prism-chat-send" type="submit">Send</button></form>';
  document.body.appendChild(btn);
  document.body.appendChild(panel);

  var log = panel.querySelector("#prism-chat-log");
  var form = panel.querySelector("#prism-chat-form");
  var input = panel.querySelector("#prism-chat-in");
  var send = panel.querySelector("#prism-chat-send");
  var expBtn = panel.querySelector("#prism-chat-exp");
  var greeted = false;

  btn.onclick = function () {
    panel.style.display = "flex"; btn.style.display = "none"; input.focus();
    if (!greeted) { greeted = true; addMsg("bot", "Ask me anything about the " + company + " search audit — I answer only from the report."); }
  };
  panel.querySelector("#prism-chat-x").onclick = function () { panel.style.display = "none"; btn.style.display = "flex"; };
  expBtn.onclick = function () {
    var max = panel.classList.toggle("pc-max");
    expBtn.textContent = max ? "⤡" : "⤢";
    expBtn.title = max ? "Restore" : "Expand";
    log.scrollTop = log.scrollHeight;
  };

  input.addEventListener("keydown", function (e) {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); form.requestSubmit(); }
  });
  form.addEventListener("submit", function (e) {
    e.preventDefault();
    var text = input.value.trim();
    if (!text) return;
    input.value = ""; addMsg("user", text); ask(text);
  });

  // in-page section jumps (event delegation)
  log.addEventListener("click", function (e) {
    var a = e.target.closest && e.target.closest("a.pc-jump");
    if (!a) return;
    var id = a.getAttribute("href").slice(1);
    var t = document.getElementById(id);
    if (t) { e.preventDefault(); t.scrollIntoView({ behavior: "smooth", block: "start" }); }
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
      else { bot.innerHTML = mdToHtml(acc); linkSections(bot); }
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
    s = s.replace(/```([\s\S]*?)```/g, function (_, c) { return "<pre><code>" + c.replace(/^\n/, "") + "</code></pre>"; });
    s = s.replace(/`([^`]+)`/g, "<code>$1</code>");
    s = s.replace(/^###\s+(.*)$/gm, "<h4>$1</h4>").replace(/^##\s+(.*)$/gm, "<h3>$1</h3>").replace(/^#\s+(.*)$/gm, "<h3>$1</h3>");
    s = s.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>").replace(/(^|[^*])\*([^*\n]+)\*/g, "$1<em>$2</em>");
    s = s.replace(/\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');
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
    ["section-financials", /\b(financials?|revenue|ebitda|margin)\b/i],
    ["section-techstack", /\b(tech stack|technology stack|search vendor|search platform)\b/i],
    ["section-traffic", /\b(traffic|engagement|bounce rate|visits)\b/i],
    ["section-competitive", /\b(competitors?|competitive landscape)\b/i],
    ["section-hiring", /\b(hiring|open roles?|job postings?)\b/i],
    ["section-roi", /\b(roi|return on investment|business case)\b/i],
    ["section-industry-context", /\b(industry context|industry benchmarks?)\b/i],
    ["section-partner", /\b(partners?|co-sell)\b/i],
    ["section-quotes", /\b(executive quotes?|earnings call)\b/i],
    ["section-case-studies", /\b(case stud(?:y|ies))\b/i],
    ["section-signals", /\b(signals?)\b/i],
    ["section-discovery", /\b(discovery questions?)\b/i],
    ["section-outreach", /\b(outreach|email sequence|campaign)\b/i],
  ];
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
