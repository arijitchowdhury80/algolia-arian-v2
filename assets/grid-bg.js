/**
 * PRISM shared animated-grid background — ONE design library for every page.
 *
 * Subtle pulsing blue squares over a faint grid, fixed behind all content at
 * z-index:-1. Vanilla JS replication of magicui/animated-grid-pattern — the same
 * animation used on the audit report pages, the landing page, and the /about page.
 *
 * Drop-in (once per page, nothing else needed — it injects its own CSS):
 *   <script src="/assets/grid-bg.js" defer></script>
 *
 * Honors prefers-reduced-motion (skips the animation entirely).
 */
(function () {
  "use strict";

  // inject the positioning CSS so pages don't each redeclare it
  var style = document.createElement("style");
  style.textContent =
    "#animated-grid{position:fixed;inset:0;width:100%;height:100%;pointer-events:none;z-index:-1}";
  document.head.appendChild(style);

  function initAnimatedGrid() {
    if (typeof document.createElementNS !== "function" || !document.body) return;
    if (document.getElementById("animated-grid")) return; // never double-init
    var NS = "http://www.w3.org/2000/svg";
    var GRID = 44, NUM = 45, MAX_OP = 0.55, MIN_OP = 0.12;

    var svg = document.createElementNS(NS, "svg");
    svg.id = "animated-grid";
    svg.setAttribute("xmlns", NS);

    var defs = document.createElementNS(NS, "defs");
    defs.innerHTML =
      '<pattern id="agp" x="0" y="0" width="' + GRID + '" height="' + GRID + '" patternUnits="userSpaceOnUse">' +
      '<path d="M' + GRID + ' 0 L 0 0 0 ' + GRID + '" fill="none" stroke="rgba(0,61,255,0.07)" stroke-width="0.8"/></pattern>';
    svg.appendChild(defs);

    var bg = document.createElementNS(NS, "rect");
    bg.setAttribute("width", "100%");
    bg.setAttribute("height", "100%");
    bg.setAttribute("fill", "url(#agp)");
    svg.appendChild(bg);

    var squares = Array.from({ length: NUM }, function () {
      var r = document.createElementNS(NS, "rect");
      r.setAttribute("width", GRID - 1);
      r.setAttribute("height", GRID - 1);
      r.style.opacity = "0";
      r.style.fill = "rgba(0,61,255,0.10)";
      svg.appendChild(r);
      return r;
    });

    document.body.insertBefore(svg, document.body.firstChild);

    function reposition(r) {
      var cols = Math.ceil(window.innerWidth / GRID) + 1;
      var rows = Math.ceil(window.innerHeight / GRID) + 1;
      r.setAttribute("x", Math.floor(Math.random() * cols) * GRID);
      r.setAttribute("y", Math.floor(Math.random() * rows) * GRID);
    }
    function pulse(r, delay) {
      setTimeout(function () {
        reposition(r);
        r.style.transition = "opacity 1.8s ease";
        r.style.opacity = String(MIN_OP + Math.random() * (MAX_OP - MIN_OP));
        setTimeout(function () {
          r.style.opacity = "0";
          setTimeout(function () { pulse(r, 0); }, 2000 + Math.random() * 1500);
        }, 1800 + Math.random() * 800);
      }, delay);
    }
    squares.forEach(function (r, i) { pulse(r, i * 200 + Math.random() * 300); });
  }

  if (window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
  if (document.readyState !== "loading") initAnimatedGrid();
  else document.addEventListener("DOMContentLoaded", initAnimatedGrid);
})();
