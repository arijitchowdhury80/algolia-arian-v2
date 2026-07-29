# UI/UX Constraints

Emphasis tiers:
- `/reports/` remains the wayfinding surface.
- Audit cards remain primary navigation controls.
- Repository structure mirrors the same hierarchy so contributors do not learn a different mental model from GitHub.

Responsive and accessibility constraints:
- Do not alter visual card markup beyond route targets in this change.
- Preserve existing card text, touch targets, and contrast.
- Browser verification must include desktop and mobile widths for the report index.

Component constraints:
- Audit cards continue to behave as links.
- Report pages must keep Cassandra chat and topbar asset links available after moving folders.
