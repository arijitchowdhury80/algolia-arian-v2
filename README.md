# Algolia Arian v2 — Search Audit Intelligence Hub

Interactive sales intelligence platform for Algolia Account Executives. Each company audit is a 5-tab SPA with competitive analysis, financial modeling, hiring signals, and a complete sales play.

## Live Demo

Deploy to Vercel:
```bash
vercel --prod
```

## Structure

```
/
├── index.html              # Hub — lists all audited companies
└── {company}/
    └── index.html          # 5-tab SPA per company
```

## Adding a New Audit

1. Run the audit skill: `/algolia-audit-report {company-slug}`
2. Regenerate index: `deno run --allow-read --allow-write ~/.claude/skills/algolia-search-audit/scripts/generate-index.ts`
3. Deploy: `vercel --prod`

## SPA Tabs

| Tab | Contents |
|-----|---------|
| Overview | Score, critical gaps, revenue at risk, golden angle, timing signals |
| Company Intel | Bento snapshot, financials, tech stack, hiring, intelligence signals |
| Search Audit | 10-area heatmap, findings with screenshots |
| Business Case | Said vs Found, competitive matrix, ROI scenarios, strategic angles |
| Sales Play | Pre-call brief, buying committee, battle card, discovery Qs, outreach plan |

## Skills

Built with [algolia-claude-skills](https://github.com/arijitchowdhury80/algolia-claude-skills).

## License

Internal Algolia tool. Not for external distribution.
