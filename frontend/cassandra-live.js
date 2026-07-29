(function () {
  "use strict";

  var STYLE_ID = "prism-cassandra-live-style";

  function injectStyle() {
    if (document.getElementById(STYLE_ID)) return;
    var style = document.createElement("style");
    style.id = STYLE_ID;
    style.textContent =
      ".cla-card{position:relative}" +
      ".cla-stage{position:relative;overflow:hidden;background:rgba(255,255,255,.06);min-height:210px}" +
      ".cla-stage img{width:100%;height:100%;object-fit:cover;object-position:center 26%;display:block}" +
      ".cla-stage iframe{position:absolute;inset:0;width:100%;height:100%;border:0;background:#050816}" +
      ".cla-stage.is-live img{opacity:0;pointer-events:none}" +
      ".cla-iframe-slot{position:absolute;inset:0}" +
      ".cla-veil{position:absolute;inset:auto 0 0;padding:18px;background:linear-gradient(180deg,transparent,rgba(11,20,48,.92));color:#fff}" +
      ".cla-veil b{display:block;font-size:13px;margin-bottom:4px}.cla-veil span{display:block;font-size:12px;color:rgba(255,255,255,.68);line-height:1.45}" +
      ".cla-actions{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-top:18px}" +
      ".cla-start,.cla-stop{border:0;border-radius:10px;padding:11px 15px;font:600 13px Sora,system-ui,sans-serif;cursor:pointer}" +
      ".cla-start{background:#fff;color:#17284b}.cla-start:hover{background:#FFE0BF}" +
      ".cla-start:disabled{opacity:.62;cursor:default}.cla-stop{background:rgba(255,255,255,.12);color:#fff;border:1px solid rgba(255,255,255,.22)}" +
      ".cla-stop[hidden]{display:none}.cla-status-text{font-size:12px;line-height:1.45;color:rgba(255,255,255,.68)}" +
      ".cla-error{color:#FFE0BF}.cla-chat{border-bottom:1px solid #eceef4;background:#fff;padding:12px 14px}" +
      ".cla-chat .cla-stage{border-radius:12px;min-height:156px;aspect-ratio:16/9;background:#101832}" +
      ".cla-chat .cla-stage img{object-position:center 20%}.cla-chat .cla-veil{padding:12px}" +
      ".cla-chat .cla-actions{margin-top:10px}.cla-chat .cla-start{background:#21243D;color:#fff;padding:9px 12px}" +
      ".cla-chat .cla-stop{background:#fff;color:#21243D;border-color:#d7dae6;padding:9px 12px}" +
      ".cla-chat .cla-status-text{color:#6B7280}.cla-chat .cla-error{color:#b4232a}";
    document.head.appendChild(style);
  }

  function mountAll() {
    injectStyle();
    Array.prototype.forEach.call(document.querySelectorAll("[data-cassandra-live]"), mount);
  }

  function mount(root) {
    if (root.getAttribute("data-cla-mounted") === "1") return;
    root.setAttribute("data-cla-mounted", "1");
    root.classList.add("cla-card");

    var start = root.querySelector(".cla-start");
    var stop = root.querySelector(".cla-stop");
    var status = root.querySelector(".cla-status-text");
    var stage = root.querySelector(".cla-stage");
    var slot = root.querySelector(".cla-iframe-slot");
    if (!start || !stop || !status || !stage || !slot) return;

    start.addEventListener("click", function () { startLive(root, start, stop, status, stage, slot); });
    stop.addEventListener("click", function () { stopLive(root, start, stop, status, stage, slot); });
  }

  async function startLive(root, start, stop, status, stage, slot) {
    start.disabled = true;
    status.textContent = "Starting LiveAvatar...";
    status.classList.remove("cla-error");
    try {
      var payload = await requestSession(root);
      if (!payload.configured || !payload.url) return showFallback(payload, start, status);
      slot.innerHTML = "";
      var iframe = document.createElement("iframe");
      iframe.src = payload.url;
      iframe.title = "Cassandra LiveAvatar";
      iframe.allow = "microphone; autoplay; fullscreen";
      iframe.setAttribute("allowfullscreen", "");
      slot.appendChild(iframe);
      stage.classList.add("is-live");
      stop.hidden = false;
      status.textContent = payload.sandbox ? "LiveAvatar sandbox is running." : "Cassandra Live is running.";
    } catch (error) {
      showFallback({ reason: "connection_error" }, start, status);
    }
  }

  async function requestSession(root) {
    var slug = root.getAttribute("data-avatar-slug") || pageSlug() || "landing";
    var response = await fetch("/api/avatar/session", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ slug: slug }),
    });
    if (!response.ok) return { configured: false, reason: "liveavatar_unavailable" };
    return response.json();
  }

  async function stopLive(root, start, stop, status, stage, slot) {
    slot.innerHTML = "";
    stage.classList.remove("is-live");
    stop.hidden = true;
    start.disabled = false;
    status.textContent = "Live avatar stopped.";
    try {
      await fetch("/api/avatar/stop", { method: "POST", headers: { "Content-Type": "application/json" } });
    } catch (error) {}
  }

  function showFallback(payload, start, status) {
    start.disabled = false;
    status.classList.add("cla-error");
    if (payload.reason === "missing_api_key") {
      status.textContent = "Live avatar is not configured in this environment yet. Cassandra chat still works from the audit.";
      return;
    }
    status.textContent = "LiveAvatar is unavailable right now. Cassandra chat still answers from the audit.";
  }

  function pageSlug() {
    var parts = location.pathname.split("/").filter(Boolean);
    if (parts[0] === "reports") return parts[1] || "";
    return parts[0] || "";
  }

  window.PrismCassandraLive = { mountAll: mountAll };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", mountAll);
  else mountAll();
})();
