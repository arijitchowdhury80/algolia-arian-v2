# MEMORY — Prism (seed)

- **What PRISM is:** an internal Algolia AE/BDR prospect-intelligence tool. The package = **this
  Hermes instance (Chowmes-PRISM) + the algolia-* skill suite**. Not a custom SaaS.
- **How it works:** control/execution split. Prism (control) dispatches a **headless Claude worker**
  that runs the 22 `algolia-*` skills to produce a scored search audit + sales deliverables.
- **Deliverables per audit:** scored SPA deck, AE pre-call report, battle card, leave-behind + PDF,
  business case (ROI), sales playbook, ABX campaign, strategic signal brief.
- **Published reports** land on the hub: `algolia-arian-v2.vercel.app/<company>/`.
- **The wedge:** the *scored search audit* + the single damning finding. Constructor.io is THE
  competitor for ICP-sized ecommerce.
- **Locked decisions:** control model = `google/gemini-2.5-flash` (OpenRouter); execution = headless
  Claude (Anthropic). **Temporal dropped** — Hermes-native kanban/cron is the orchestrator.
- **Skills source of truth:** the `arijit-skills` repo (`skills/algolia-audit-skills`); it carries
  the financials-chart parser fix. Skills run on the executor, not on Prism's own model.
- **Two interaction modes:** generation (batch audit) vs consumption (chat over a finished report).
