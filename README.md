# Algolia Search Audit Intelligence Hub

Interactive sales intelligence platform for Algolia Account Executives. Each company audit is a 5-tab SPA with competitive analysis, financial modelling, browser findings, hiring signals, and a complete sales play.

**Live:** https://algolia-arian-v2.vercel.app/

---

## Audits

| Company | Vertical | Score | Factcheck | Vercel URL |
|---------|---------|-------|-----------|------------|
| **La Banque Postale** | French Retail Banking | 2.1/10 | PROCEED 9.1/10 | [/labanquepostale/](https://algolia-arian-v2.vercel.app/labanquepostale/index.html) |
| **British Airways** | Airline / Travel | 2.1/10 | Corrections applied | [/british-airways/](https://algolia-arian-v2.vercel.app/british-airways/index.html) |
| **Brooks Running** | Performance Footwear | — | — | [/brooks-running/](https://algolia-arian-v2.vercel.app/brooks-running/index.html) |
| **DSW** | Footwear Retail | — | — | [/dsw/](https://algolia-arian-v2.vercel.app/dsw/index.html) |
| **L.L.Bean** | Outdoor Retail | — | — | [/llbean/](https://algolia-arian-v2.vercel.app/llbean/index.html) |
| **Savage X Fenty** | DTC Lingerie | — | — | [/savage-x-fenty/](https://algolia-arian-v2.vercel.app/savage-x-fenty/index.html) |
| **Nike** | Athletic Apparel | — | — | [/nike/](https://algolia-arian-v2.vercel.app/nike/index.html) |
| **Oriental Trading** | Party & Craft Retail | — | — | [/orientaltrading/](https://algolia-arian-v2.vercel.app/orientaltrading/index.html) |

---

## Repo Structure

```
/
├── index.html                     # Hub — lists all audited companies
├── {slug}-audit-data.json         # Audit data (stays at root)
├── {slug}/
│   ├── index.html                 # 5-tab SPA
│   ├── ae-report.html             # AE pre-call report
│   ├── battle-card.html           # Competitive battle card
│   ├── leave-behind.html          # Prospect leave-behind
│   └── screenshots/               # Browser audit evidence
└── publish.sh                     # Publish helper
```

---

## SPA Tabs

| Tab | Contents |
|-----|---------|
| Overview | Score, critical gaps, revenue at risk, golden angle, timing signals |
| Company Intel | Bento snapshot, financials, tech stack, hiring, intelligence signals |
| Search Audit | 10-area heatmap, findings with screenshots |
| Business Case | ROI model, competitive matrix, strategic angles |
| Sales Play | Pre-call brief, buying committee, battle card, discovery Qs, outreach plan |

---

## Adding a New Audit

1. Run research: `algolia-audit-research {domain}`
2. Run browser testing: `algolia-audit-browser {company}`
3. Generate report: `algolia-audit-report {company}`
4. Run factcheck: `algolia-audit-factcheck {company}` — must PROCEED before sharing
5. Copy `{company}/deliverables/` → `/{slug}/` in this repo, push to main — Vercel auto-deploys

---

Built with [Algolia Claude Skills](https://github.com/arijitchowdhury80/algolia-claude-skills) — internal Algolia tool.
