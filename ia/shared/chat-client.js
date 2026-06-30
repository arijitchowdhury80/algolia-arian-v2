// ia/shared/chat-client.js -- reuses the existing /api/chat backend, forces the correct slug
const SLUG = "homedepot-mexico";
const JOB_HINTS = [
  { re: /battle|competitor|constructor|coveo/i, job: "convo" },
  { re: /roi|revenue|money|value|opportunity/i, job: "money" },
  { re: /finding|broken|search quality|zero result/i, job: "broken" },
  { re: /who|buyer|committee|champion|meddpicc/i, job: "who" },
  { re: /email|outreach|abx|sequence|linkedin/i, job: "reach" },
  { re: /company|traffic|stack|hiring|financial/i, job: "account" },
];
function sid() {
  let s = localStorage.getItem("prism_ia_sid");
  if (!s) { s = "ia-" + Math.abs(Date.now() ^ (location.pathname.length * 2654435761)).toString(36); localStorage.setItem("prism_ia_sid", s); }
  return s;
}
export function createChat({ mount, onOpenFull }) {
  const log = document.createElement("div");
  log.className = "ia-chatlog";
  mount.appendChild(log);
  function bubble(role, text) {
    const d = document.createElement("div");
    d.className = "ia-msg ia-" + role;
    d.textContent = text;
    log.appendChild(d);
    log.scrollTop = log.scrollHeight;
    return d;
  }
  async function send(text) {
    if (!text || !text.trim()) return;
    bubble("user", text);
    const out = bubble("bot", "");
    try {
      const res = await fetch("/api/chat", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text, slug: SLUG, sid: sid() }),
      });
      const reader = res.body.getReader();
      const dec = new TextDecoder();
      let full = "";
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        full += dec.decode(value, { stream: true });
        out.textContent = full;
        log.scrollTop = log.scrollHeight;
      }
      const hint = JOB_HINTS.find((h) => h.re.test(text) || h.re.test(full));
      if (hint && onOpenFull) {
        const btn = document.createElement("button");
        btn.className = "ia-export-btn";
        btn.textContent = "Open full";
        btn.onclick = () => onOpenFull(hint.job);
        out.appendChild(document.createElement("br"));
        out.appendChild(btn);
      }
    } catch (e) {
      out.textContent = "Chat is unavailable right now.";
    }
  }
  return { send, el: log };
}
