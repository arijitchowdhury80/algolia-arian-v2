import { buildModel } from "../shared/job-model.js";
import { renderBrief, renderPanel, renderProspect, renderExports } from "../shared/render.js";
import { createChat } from "../shared/chat-client.js";
import { mountFeedback } from "../shared/feedback.js";

const data = await (await fetch("/homedepot-mexico-audit-data.json")).json();
const model = buildModel(data);
let mode = "seller";

document.getElementById("ia-title").textContent = "PRISM IA2 (chat) " + model.brief.company;
document.getElementById("ia-brief-host").innerHTML = renderBrief(model.brief);

const panelHost = document.getElementById("ia-panel-host");
function showJob(id) {
  const job = model.jobs.find((j) => j.id === id);
  panelHost.innerHTML = renderPanel(job) + renderExports(model.exports);
  panelHost.scrollIntoView({ behavior: "smooth" });
}

const chat = createChat({ mount: document.getElementById("ia-chat-mount"), onOpenFull: showJob });
document.getElementById("ia-ask-send").onclick = () => { const i = document.getElementById("ia-ask-input"); chat.send(i.value); i.value = ""; };

const CHIPS = [
  ["battle card vs incumbent", "convo"], ["ROI at +2% conversion", "money"],
  ["who's on the call", "who"], ["what do I send after the call", "reach"],
  ["how bad is their search", "broken"], ["company snapshot", "account"],
];
const chipHost = document.getElementById("ia-chips");
CHIPS.forEach(([label]) => {
  const c = document.createElement("button");
  c.className = "ia-chip"; c.textContent = label;
  c.onclick = () => chat.send(label);
  chipHost.appendChild(c);
});

const rail = document.getElementById("ia-rail");
model.jobs.forEach((j) => {
  const b = document.createElement("button");
  b.dataset.job = j.id; b.textContent = j.label;
  b.onclick = () => { showJob(j.id); document.getElementById("ia-browse-drawer").classList.remove("open"); };
  rail.appendChild(b);
});
document.getElementById("ia-browse-all").onclick = () => document.getElementById("ia-browse-drawer").classList.toggle("open");

function applyMode() {
  document.getElementById("m-seller").classList.toggle("active", mode === "seller");
  document.getElementById("m-prospect").classList.toggle("active", mode === "prospect");
  const sellerOnly = [document.querySelector(".ia-ask"), chipHost, document.getElementById("ia-chat-mount"), document.getElementById("ia-browse-all")];
  if (mode === "prospect") { sellerOnly.forEach((e) => e.style.display = "none"); panelHost.innerHTML = renderProspect(model.prospect); }
  else { sellerOnly.forEach((e) => e.style.display = ""); panelHost.innerHTML = ""; }
}
document.getElementById("m-seller").onclick = () => { mode = "seller"; applyMode(); };
document.getElementById("m-prospect").onclick = () => { mode = "prospect"; applyMode(); };

applyMode();
mountFeedback("ia2");
