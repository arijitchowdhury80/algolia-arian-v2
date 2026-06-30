/**
 * PRISM report-chat widget — drop-in for every published audit page.
 *
 * A floating "Ask about this audit" panel. Reads the company slug from the URL
 * (/<slug>/), streams grounded answers from /api/chat (→ Hermes-PRISM report-QA,
 * the same brain as the Telegram bot). Answers come ONLY from this company's audit;
 * anything not in the report is refused by the Hermes grounding gate.
 *
 * Include once per page:  <script src="/chat-widget.js" defer></script>
 */
(function () {
  "use strict";

  // --- which company is this page about? ---
  var slug = (location.pathname.split("/").filter(Boolean)[0] || "").toLowerCase();
  if (!slug || slug === "index.html") return; // hub homepage: no single report to ground

  // --- stable per-visitor id (thread continuity within this browser) ---
  var sid;
  try {
    sid = localStorage.getItem("prism_sid");
    if (!sid) {
      sid = "v" + Math.random().toString(36).slice(2, 12);
      localStorage.setItem("prism_sid", sid);
    }
  } catch (e) {
    sid = "v" + Math.random().toString(36).slice(2, 12);
  }

  // --- styles ---
  var css =
    "#prism-chat-btn{position:fixed;bottom:24px;right:24px;z-index:99999;height:54px;padding:0 22px;border:0;border-radius:27px;background:#21243D;color:#fff;font-family:'Sora',sans-serif;font-size:15px;font-weight:600;cursor:pointer;box-shadow:0 8px 28px rgba(33,36,61,.32);display:flex;align-items:center;gap:9px}" +
    "#prism-chat-btn:hover{background:#2c3050}" +
    "#prism-chat-panel{position:fixed;bottom:24px;right:24px;z-index:99999;width:390px;max-width:calc(100vw - 32px);height:560px;max-height:calc(100vh - 48px);background:#fff;border-radius:16px;box-shadow:0 24px 64px rgba(33,36,61,.30);display:none;flex-direction:column;overflow:hidden;font-family:'Sora',sans-serif}" +
    "#prism-chat-head{background:#21243D;color:#fff;padding:16px 18px;display:flex;align-items:center;gap:10px}" +
    "#prism-chat-head .t{font-size:15px;font-weight:600}#prism-chat-head .s{font-size:12px;color:rgba(255,255,255,.55);margin-top:2px}" +
    "#prism-chat-head .av{width:40px;height:40px;border-radius:50%;object-fit:cover;object-position:center top;flex-shrink:0;border:2px solid rgba(255,255,255,.25)}" +
    "#prism-chat-x{margin-left:auto;background:0;border:0;color:rgba(255,255,255,.7);font-size:22px;cursor:pointer;line-height:1}" +
    "#prism-chat-log{flex:1;overflow-y:auto;padding:18px;background:#F8F9FB;display:flex;flex-direction:column;gap:12px}" +
    ".pc-msg{max-width:85%;padding:11px 14px;border-radius:13px;font-size:14px;line-height:1.5;white-space:pre-wrap;word-wrap:break-word}" +
    ".pc-user{align-self:flex-end;background:#21243D;color:#fff;border-bottom-right-radius:4px}" +
    ".pc-bot{align-self:flex-start;background:#fff;color:#23263B;border:1px solid #e7e9f0;border-bottom-left-radius:4px}" +
    ".pc-bot.err{color:#b4232a;border-color:#f3d0d2}" +
    "#prism-chat-form{display:flex;gap:8px;padding:14px;border-top:1px solid #eceef4;background:#fff}" +
    "#prism-chat-in{flex:1;border:1px solid #d7dae6;border-radius:10px;padding:10px 12px;font-family:inherit;font-size:14px;resize:none;outline:0;max-height:96px}" +
    "#prism-chat-in:focus{border-color:#21243D}" +
    "#prism-chat-send{border:0;border-radius:10px;background:#21243D;color:#fff;padding:0 16px;font-family:inherit;font-size:14px;font-weight:600;cursor:pointer}" +
    "#prism-chat-send:disabled{opacity:.5;cursor:default}";
  var style = document.createElement("style");
  style.textContent = css;
  document.head.appendChild(style);

  // --- elements ---
  var company = slug.replace(/-/g, " ").replace(/\b\w/g, function (c) { return c.toUpperCase(); });
  var btn = el("button", { id: "prism-chat-btn" });
  btn.innerHTML = "<span>🔍</span> Ask about this audit";
  var panel = el("div", { id: "prism-chat-panel" });
  panel.innerHTML =
    '<div id="prism-chat-head"><img class="av" src="/assets/cassandra.png" alt="Cassandra" /><div><div class="t">Cassandra</div><div class="s">Grounded in the ' + escapeHtml(company) + " audit</div></div><button id=\"prism-chat-x\" aria-label=\"close\">×</button></div>" +
    '<div id="prism-chat-log"></div>' +
    '<form id="prism-chat-form"><textarea id="prism-chat-in" rows="1" placeholder="Ask anything about this audit…"></textarea><button id="prism-chat-send" type="submit">Send</button></form>';
  document.body.appendChild(btn);
  document.body.appendChild(panel);

  var log = panel.querySelector("#prism-chat-log");
  var form = panel.querySelector("#prism-chat-form");
  var input = panel.querySelector("#prism-chat-in");
  var send = panel.querySelector("#prism-chat-send");
  var greeted = false;

  btn.onclick = function () {
    panel.style.display = "flex";
    btn.style.display = "none";
    input.focus();
    if (!greeted) {
      greeted = true;
      addMsg("bot", "Ask me anything about the " + company + " search audit — I answer only from the report.");
    }
  };
  panel.querySelector("#prism-chat-x").onclick = function () {
    panel.style.display = "none";
    btn.style.display = "flex";
  };
  input.addEventListener("keydown", function (e) {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); form.requestSubmit(); }
  });

  form.addEventListener("submit", function (e) {
    e.preventDefault();
    var text = input.value.trim();
    if (!text) return;
    input.value = "";
    addMsg("user", text);
    ask(text);
  });

  async function ask(text) {
    send.disabled = true;
    var bot = addMsg("bot", "");
    bot.textContent = "…";
    try {
      var res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text, slug: slug, sid: sid }),
      });
      if (!res.ok || !res.body) {
        bot.textContent = "Sorry — the audit chat is unavailable right now.";
        bot.classList.add("err");
        return;
      }
      var reader = res.body.getReader();
      var dec = new TextDecoder();
      var acc = "";
      for (;;) {
        var r = await reader.read();
        if (r.done) break;
        acc += dec.decode(r.value, { stream: true });
        bot.textContent = acc;
        log.scrollTop = log.scrollHeight;
      }
      if (!acc.trim()) bot.textContent = "(no response)";
    } catch (err) {
      bot.textContent = "Connection error. Please try again.";
      bot.classList.add("err");
    } finally {
      send.disabled = false;
      input.focus();
    }
  }

  function addMsg(role, text) {
    var m = el("div", { class: "pc-msg " + (role === "user" ? "pc-user" : "pc-bot") });
    m.textContent = text;
    log.appendChild(m);
    log.scrollTop = log.scrollHeight;
    return m;
  }
  function el(tag, attrs) {
    var n = document.createElement(tag);
    for (var k in attrs) n.setAttribute(k === "class" ? "class" : k, attrs[k]);
    return n;
  }
  function escapeHtml(s) {
    return s.replace(/[&<>"]/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
    });
  }
})();
