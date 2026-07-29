# Phase 1 research: can Algolia be PRISM's database + index layer?

Fresh research (no prior art found — confirmed via vault + repo search). Method: read the local Algolia API reference (`vault Projects/algolia-central2/wiki/reference/algolia-api/`, mirrored from `Algolia-Central2/docs/algolia-api/`) plus a live empirical probe against a real Algolia app (CENTRAL, `0EXRPAXB56`) using the connected `mcp__algolia__*` tools — not just doc-reading, matching the rigor of the existing Agent Studio research.

## What Algolia's write/read API actually gives you

- **Document store semantics**: `saveObject`/`addOrUpdateObject`/`partialUpdateObject` — schemaless JSON records, full-replace or partial-update, with built-in atomic-ish field operations (`Increment`, `Decrement`, `Add`, `Remove`, `AddUnique`). This is a genuine NoSQL-document-store write API, not just a search-ingestion pipe.
- **Batch operations**: `batch` (single index) and `multipleBatch` (cross-index in one request) — real bulk write capability.
- **Reads**: `getObject` (single, by ID) and `getObjects` (many, cross-index, one round-trip) — direct key-value style lookups, separate from `searchSingleIndex`.
- **Index lifecycle**: copy/move/list/delete indices — this is closer to "table" management than a pure search feature.

## Consistency model — the one documented gotcha, empirically tested

**Documented:** every write returns a `taskID` and a "queued" response, not "applied." The docs explicitly warn: *"a 200/201 means queued, not applied — always poll `getTask` before reading back or chaining dependent operations."*

**Live-tested (this session, 2026-07-04):** wrote one record to a throwaway index, immediately called `getObject` (no wait) — succeeded instantly with correct data. Immediately called `getTask` — already `published`. Immediately ran `searchSingleIndex` (a different code path, full search-index rebuild not just KV lookup) — also found the record, fully indexed, in 15ms processing time. Total elapsed wall-clock across all 4 calls: a couple seconds.

**Verdict on this specific point:** for small, single-record writes, real-world latency is very fast — matches Algolia's "near real-time" claims. But this was ONE record, tested once, on a low-traffic app. The docs' own advice (always poll before depending on the result) is the safe engineering default; I have not tested behavior under bulk writes, large batches, or sustained load, and shouldn't assume this single fast result generalizes to every scenario. If PRISM built an executioner that treats every write as durable-and-readable immediately, it would be building against undocumented/untested behavior, not a guarantee.

## What's fundamentally missing (this is the real finding)

Algolia's write/read API, however capable, is missing several things a traditional database gives for free:

1. **No ACID transactions.** Nothing in this API commits multiple writes atomically across records or indices. `multipleBatch` sends several operations in one HTTP request, but there's no rollback-on-partial-failure guarantee documented — each operation in the batch is still an independent async task.
2. **No joins / relational queries.** `getObjects` can fetch many records by ID across indices in one round trip, but that's a batched key lookup, not a relational join — there's no way to ask "give me all findings where audit.company = X and finding.severity = critical" across two related record types in one query the way SQL would. You'd either denormalize everything an audit needs into one record (duplication, and unknown per-record size ceiling — not verified in this pass), or do multiple lookups and stitch client-side (no cross-record atomicity).
3. **No structured query language beyond filter/facet syntax.** The `filters`/`facetFilters`/`numericFilters` params (documented in `01-search-api.md`) cover a lot — AND/OR/NOT, ranges, numeric comparisons — but it's a filter DSL over indexed attributes, not general-purpose relational querying.
4. **Cost model is unverified for this use case.** Algolia's pricing is built around search operations + records stored, optimized for "index for search" workloads. Using it as the sole backend for PRISM's full data (job state, structured audit metadata, research corpus, everything) would mean every internal read/write the executioner does also counts as billable API usage — I have not investigated actual pricing tiers or whether this would be cost-competitive with a normal Postgres instance for PRISM's access patterns. Flagging as unresearched, not concluding either way.

## Working synthesis (not a final decision — bring to Arijit)

Two different things are being asked in "can Algolia be the database," and the honest answer differs by which one:

- **As a document store + search layer for PRISM's actual content** (audit-data.json documents, research corpus, generated report bodies) — this looks genuinely viable. It's close to what Algolia-Central2 already does successfully (a RAG corpus on Algolia), and PRISM's content is exactly the kind of thing that benefits from being searchable/retrievable this way. This is a real, positive finding.
- **As the executioner's state-tracking database** (job status, "is step 3 of this audit done yet," dependencies between pipeline steps, mandatory factcheck-gate pass/fail records) — this looks like a weaker fit. That workload wants exactly what's missing above: transactional guarantees, relational structure between a job and its steps, and query patterns beyond filter/facet. Async-by-design indexing (even if fast in practice) is the wrong default assumption for "did step 3 definitely finish and can step 4 safely start."

**Recommendation for the next research pass, not a conclusion:** consider a split architecture — Algolia for the searchable content layer (matches its strength, reuses what Agent Studio can already query), plus something else (a real database, or Algolia's native conversation/task metadata if that turns out to be enough) for the executioner's own state tracking. This directly feeds back into the still-open executioner question (`00-manifesto.md` Phase 1) — Temporal's own state model may be exactly what covers the second half of this gap, which strengthens rather than replaces the "Temporal as executioner" lean already in the manifesto.

## Open items for a future pass
- Actual per-record and per-index size limits (not found in the local API reference; flagged as unverified rather than assumed from general knowledge).
- Behavior under bulk writes / sustained load (this pass only tested one record).
- Real cost modeling for PRISM's access-pattern volume.
- Whether Algolia's native conversation/transcript store (`GET /agents/{id}/conversations`, seen in the Agent Studio research, 90-day retention) could cover *some* of the executioner's state-tracking need, reducing how much a second system needs to own.
