# Test Queries — Dell Technologies
*Generated: 2026-06-30 | Vertical: Technology hardware & enterprise IT (PCs, laptops, monitors, servers, storage, networking) | B2B + B2C direct ecommerce | Search vendor: Bloomreach*

## Query Set (18 queries)

These queries are grounded in Dell's actual catalog (XPS, Alienware, Latitude, PowerEdge, UltraSharp, OptiPlex, Inspiron) and its dual B2B/B2C model. They are deliberately engineered to expose keyword-era weaknesses in Bloomreach: NLP/semantic gaps, typo tolerance, synonym coverage, zero-results dead ends, cross-sell/upsell failures, and B2B-specific patterns (part numbers, SKU/spec-driven search).

### Broad Category Queries
1. "laptops" — [Client Solutions / PCs] — Tests: SAYT response speed, breadth of autocomplete, whether consumer (XPS/Inspiron) and commercial (Latitude) lines are surfaced together or split
2. "monitors" — [Peripherals / Displays] — Tests: result quality, facet availability (size, resolution, panel type, refresh rate), merchandising of UltraSharp vs gaming vs budget

### Specific Product Queries
3. "XPS 15 laptop" — [Premium consumer laptop] — Tests: precision search, does it return the current XPS 15 config page or a scatter of accessories/parts
4. "PowerEdge R760" — [Enterprise rack server, SKU-level] — Tests: B2B SKU-level relevance, whether a spec'd server model resolves to a configurable product or dead-ends into support docs

### NLP / Conversational
5. "best laptop for video editing" — Tests: semantic intent understanding — does it map to high-RAM/discrete-GPU/color-accurate-display SKUs, or keyword-match the literal words and fail
6. "laptop with good battery life for travel under 1000" — Tests: multi-attribute NLP (use-case + battery attribute + price ceiling) — the hardest combined-intent query
7. "gaming pc with rtx 4070 and 32gb ram" — Tests: spec-driven multi-attribute parsing (GPU model + memory) — a core B2C enthusiast + B2B workstation pattern that keyword search typically mishandles

### Typo Variants
8. "alienwear" → correct: "Alienware" — Tests: typo tolerance on Dell's flagship gaming sub-brand (missing/altered letters)
9. "dell latitide laptop" → correct: "Dell Latitude laptop" — Tests: correction prompt on a high-volume commercial line (transposition/missing letter); "latitide" for "latitude"

### Synonym / Colloquial
10. "notebook" vs "laptop" — Tests: synonym handling — "notebook" is the formal/legacy term Dell itself uses in product taxonomy; will a shopper searching the colloquial mismatch get parity
11. "desktop tower" vs "desktop computer" vs "workstation" — Tests: language normalization across colloquial ("tower"), category ("desktop"), and B2B ("Precision workstation") terms for the same intent

### Non-Product Content
12. "return policy" — Tests: federated search — does non-product support/policy content surface in results, or does search only index the product catalog
13. "order status" OR "track my order" — Tests: content/tool integration — does search route to order tracking (a top self-service intent) or return zero product results

### Brand Queries
14. "Alienware" — Tests: brand/sub-brand intent detection — does it land on the Alienware brand hub/category or scatter individual SKUs
15. "Intel Core Ultra" vs "NVIDIA RTX" — Tests: vendor/component brand filtering — do component-brand searches resolve to filtered product lists (a key B2B spec-driven pattern)

### No-Results Recovery
16. "asdfghjk" — Tests: zero-results handling — is there a graceful empty state with suggestions/popular products, or a dead-end blank page

### B2B-Specific / SKU & Part-Number (bonus — Dell's dominant revenue is B2B)
17. "210-AKXX" — Tests: part-number / order-code search — Dell publishes order codes (e.g. 210-Axxx format) throughout its B2B catalog; does search resolve a raw part/order code to the product, or fail entirely
18. "docking station for latitude 7450" — Tests: cross-sell / compatibility search — does search understand accessory-to-base-unit compatibility (dock ↔ specific laptop model), the classic B2B upsell/attach opportunity keyword search misses

---

## Browser Audit Mapping

| Step | Query to use | What to test |
|------|-------------|--------------|
| 2c SAYT | Query 1 ("laptops") | Autocomplete speed + content richness |
| 2d Results | Query 2 ("monitors") | Result quality + facets (size/resolution/panel) |
| 2e Typo | Query 8 ("alienwear") | Typo tolerance + correction prompt on flagship brand |
| 2f Synonym | Query 10 ("notebook" vs "laptop") | Synonym recognition / parity |
| 2g No-results | Query 16 ("asdfghjk") | Zero-results empty state |
| 2h Non-product | Query 12 ("return policy") | Content federation |
| 2m NLP | Query 6 ("laptop with good battery life for travel under 1000") | Semantic multi-attribute understanding |
| 2n B2B SKU | Query 17 ("210-AKXX") | Part-number / order-code resolution |
| 2o Cross-sell | Query 18 ("docking station for latitude 7450") | Accessory-to-base compatibility / attach upsell |

---

## Query Source Notes

- **Vertical & catalog basis:** Derived from `01-company-context.md` — Dell sells PCs, laptops, monitors, servers, storage, networking; portfolio brands Alienware (gaming), Dell EMC (infrastructure). Product-line names (XPS, Inspiron, Latitude, OptiPlex, Precision, PowerEdge, UltraSharp) are Dell's documented consumer/commercial taxonomy.
- **B2B weighting:** `01-company-context.md` states B2B is Dell's dominant revenue stream (PremierConnect, APEX, enterprise). Queries 4, 15, 17, 18 deliberately target B2B search patterns — SKU/model precision, component-brand filtering, raw part/order codes, and compatibility cross-sell — because these are where keyword-era search most often fails enterprise buyers.
- **Typo derivation:** `03-traffic-data.md` returned no usable SimilarWeb keywords (all endpoints 401 Unauthorized). Typo variants were therefore derived from Dell's highest-intent branded terms per domain knowledge: "Alienware" (→ "alienwear") and "Latitude" (→ "latitide"), both flagship high-volume lines where a correction failure directly costs conversions.
- **Synonym basis:** Dell's own taxonomy uses "notebook" and "Precision workstation" formally, while shoppers search "laptop," "tower," and "desktop" — Queries 10–11 test whether Bloomreach bridges Dell's internal taxonomy language to natural shopper language.
- **NLP basis:** Queries 5–7 mirror real shopping/procurement phrasing (use-case, budget ceiling, and hardware-spec combinations) to test semantic intent vs literal keyword matching.
- **Non-product basis:** "return policy" and "order status" are top self-service intents for a direct-sales ecommerce model; they test whether Dell's search federates support/tools content or is catalog-only.
- **Tech-stack context:** `02-tech-stack.md` confirms Bloomreach (keyword-era vendor) with Angular front end, likely server-side rendered. Browser auditor should expect Akamai/Cloudflare/Fastly WAF layering — coverage may be partial under bot detection.
