// ia/shared/feedback.js — in-prototype feedback widget
export function mountFeedback(shell) {
  const sid = localStorage.getItem("prism_ia_sid") || "anon";
  const box = document.createElement("div");
  box.style.cssText = "position:fixed;bottom:20px;left:20px;z-index:9999;";
  box.innerHTML = `<details class="ia-card" style="max-width:300px;background:#fff;">
    <summary>Feedback on this view</summary>
    <p>Easy to find what you needed?</p>
    <button data-r="easy">Easy</button> <button data-r="ok">OK</button> <button data-r="hard">Confusing</button>
    <textarea id="ia-fb-text" placeholder="What was missing or confusing?" style="width:100%;margin-top:8px;"></textarea>
    <p>Which approach do you prefer overall?</p>
    <button data-p="ia1">Browse (IA1)</button> <button data-p="ia2">Chat (IA2)</button>
    <div id="ia-fb-done" style="color:green;"></div>
  </details>`;
  document.body.appendChild(box);
  let rating = "", preference = "";
  async function post() {
    try {
      await fetch("/api/feedback", { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ shell, rating, preference, text: box.querySelector("#ia-fb-text").value, sid }) });
      box.querySelector("#ia-fb-done").textContent = "Thanks, recorded.";
    } catch { box.querySelector("#ia-fb-done").textContent = "Saved locally."; }
    localStorage.setItem("prism_ia_fb_" + shell, JSON.stringify({ rating, preference, t: box.querySelector("#ia-fb-text").value }));
  }
  box.querySelectorAll("[data-r]").forEach((b) => b.onclick = () => { rating = b.dataset.r; post(); });
  box.querySelectorAll("[data-p]").forEach((b) => b.onclick = () => { preference = b.dataset.p; post(); });
}
