# Reports IA Design Thinking

Mental model: the user sees PRISM as a library of published audits. The root is the product front door; `/reports/` is the shelf where every audit lives.

Information architecture:
- Hero: `/reports/index.html`, the audit library.
- Primary: `/reports/{account}/`, each published five-tab audit and its sales assets.
- Secondary: `/reports/data/`, the audit data snapshots used for publishing, prototypes, and provenance.
- Supporting: root `api/`, `server/`, `assets/`, `tests/`, `docs/`, and IA prototypes.

Interaction flow:
1. User opens `/reports/`.
2. User picks an audit card.
3. Card opens `/reports/{account}/`.
4. Audit topbar exposes the report assets inside the same account folder.

Cognitive load budget: the repo root should not list every customer account. Customer-specific material belongs in one scannable subtree.

Emotional target: the GitHub repo should feel like a product with an organized archive, not a dump of generated folders.

Pre-mortem:
- Risk: moved pages break asset links. Mitigation: browser-check moved routes and download links.
- Risk: next publish writes to root again. Mitigation: update and test `publish.sh`.
- Risk: old public URLs break. Mitigation: add Vercel redirects from legacy root audit URLs to `/reports/{slug}/`.
