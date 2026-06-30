// ia/ia1/ia1.js - IA1 browse-centric shell (brief + jobs rail + panels + helper chat + mode toggle)
import { buildModel } from "../shared/job-model.js";
import { renderBrief, renderPanel, renderProspect, renderExports } from "../shared/render.js";
import { createChat } from "../shared/chat-client.js";
import { mountFeedback } from "../shared/feedback.js";

let data, model;
try {
  data = await (await fetch("/homedepot-mexico-audit-data.json")).json();
  model = buildModel(data);
} catch (_e) {
  document.getElementById("ia-brief-host").innerHTML = "Could not load the audit data. Check the data file path.";
  throw _e;
}
let mode = "seller";

document.getElementById("ia-title").textContent = "PRISM IA1 (browse) " + model.brief.company;
document.getElementById("ia-brief-host").innerHTML = renderBrief(model.brief);

const rail = document.getElementById("ia-rail");
const main = document.getElementById("ia-main");

function showJob(id) {
  const job = model.jobs.find((j) => j.id === id);
  main.innerHTML = renderPanel(job) + renderExports(model.exports);
  [...rail.children].forEach((b) => b.classList.toggle("active", b.dataset.job === id));
}
function renderRail() {
  rail.innerHTML = "";
  model.jobs.forEach((j) => {
    const b = document.createElement("button");
    b.dataset.job = j.id; b.textContent = j.label;
    b.onclick = () => showJob(j.id);
    rail.appendChild(b);
  });
}
function applyMode() {
  document.getElementById("m-seller").classList.toggle("active", mode === "seller");
  document.getElementById("m-prospect").classList.toggle("active", mode === "prospect");
  if (mode === "prospect") { rail.style.display = "none"; main.innerHTML = renderProspect(model.prospect); }
  else { rail.style.display = ""; renderRail(); showJob("account"); }
}
document.getElementById("m-seller").onclick = () => { mode = "seller"; applyMode(); };
document.getElementById("m-prospect").onclick = () => { mode = "prospect"; applyMode(); };

const chat = createChat({ mount: document.getElementById("ia-chat-mount"), onOpenFull: (job) => { mode = "seller"; applyMode(); showJob(job); } });
document.getElementById("ia-chat-toggle").onclick = () => document.getElementById("ia-chat-drawer").classList.toggle("open");
document.getElementById("ia-chat-send").onclick = () => { const i = document.getElementById("ia-chat-input"); chat.send(i.value); i.value = ""; };

applyMode();
mountFeedback("ia1");
