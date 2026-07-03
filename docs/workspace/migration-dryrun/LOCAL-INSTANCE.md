# PRISM Local Instance -- persistent Postgres + browsable reports

Runs entirely on this machine. The live VPS and live Postgres were never touched.
Data lives in a **persistent** `postgres:16` Docker container (`prism-local-db`,
named volume `prism-local-pgdata`) on `127.0.0.1:55432` -- it is NOT torn down
after this script runs, and survives `docker stop` / machine restarts.

Generated: 2026-07-02 18:15:50 EDT

## How to start/stop

```bash
# Start (or reuse) the persistent local DB:
docker start prism-local-db   # no-op if already running

# Re-run the migration (idempotent -- safe any time):
python3 scripts/migration/run_local_migration.py

# Start the local browsable server (serves FROM the DB):
python3 -m scripts.migration.serve_local
# then open http://127.0.0.1:8099/

# Stop the DB when done (data persists in the named volume):
docker stop prism-local-db
```

## Round-trip result

- Slugs processed: 18
- Round-trip PASS: 18
- Round-trip FAIL: 0
- Load errors: 0
- Verifies: `audits.audit_data` deep-equals the source `window.AUDIT_DATA` blob, `audits.score` matches the parsed `score.overall` **exactly** (now that the column is `Numeric(3,2)` -- jbl=1.93, nike=4.32 both store and read back with no rounding), and `accounts.domain` matches the canonical domain.

## Local DB rowcounts

- `accounts`: 17
- `audits`: 18
- `module_executions`: 180
- `deliverables`: 0

Check live any time with:
```bash
docker exec -it prism-local-db psql -U prism -d prism -c "SELECT count(*) FROM accounts;"
```

## Per-slug results

| slug | domain | score | #module_execs | round-trip |
|---|---|---|---|---|
| british-airways | britishairways.com | 2.1 | 10 | PASS |
| brooks-running | brooksrunning.com | 4.3 | 10 | PASS |
| dell | dell.com | 2.7 | 10 | PASS |
| dsw | dsw.com | 3.8 | 10 | PASS |
| footlocker | footlocker.com | 3.2 | 10 | PASS |
| homedepot-mexico | homedepot.com.mx | 2.6 | 10 | PASS |
| jbl | jbl.com | 1.93 | 10 | PASS |
| labanquepostale | labanquepostale.fr | 2.1 | 10 | PASS |
| llbean | llbean.com | 3.6 | 10 | PASS |
| lululemon | lululemon.com | 4.3 | 10 | PASS |
| michaelkors | michaelkors.com | 1.9 | 10 | PASS |
| nike | nike.com | 4.32 | 10 | PASS |
| oriental-trading | orientaltrading.com | 2.6 | 10 | PASS |
| orientaltrading | orientaltrading.com | 2.6 | 10 | PASS |
| petsmart | petsmart.com | 5.8 | 10 | PASS |
| savage-x-fenty | savagex.com | 3.5 | 10 | PASS |
| thenorthface | thenorthface.com | 4.8 | 10 | PASS |
| torrid | torrid.com | 3.0 | 10 | PASS |

## Local instance URL

`http://127.0.0.1:8099/` -- index page listing every migrated audit with score + link.
Each report page is rendered by pulling `audit_data` for that slug out of
Postgres and injecting it into the published report shell -- provably served
from the DB, not the static file on disk.

## Verification (2026-07-02, manual curl run)

```
$ curl -sS -o /dev/null -w "index: HTTP %{http_code}\n" http://127.0.0.1:8099/
index: HTTP 200
$ curl -sS -o /dev/null -w "lululemon: HTTP %{http_code}\n" http://127.0.0.1:8099/lululemon/
lululemon: HTTP 200
$ curl -sS -o /dev/null -w "jbl: HTTP %{http_code}\n" http://127.0.0.1:8099/jbl/
jbl: HTTP 200
$ curl -sS -o /dev/null -w "nike: HTTP %{http_code}\n" http://127.0.0.1:8099/nike/
nike: HTTP 200
$ curl -sS -o /dev/null -w "chat-widget.js (expect 404): HTTP %{http_code}\n" http://127.0.0.1:8099/chat-widget.js
chat-widget.js (expect 404): HTTP 404
$ curl -sS -o /dev/null -w "nonexistent-slug: HTTP %{http_code}\n" http://127.0.0.1:8099/does-not-exist/
nonexistent-slug: HTTP 404
```

Server log for the same run, proving each report is sourced from Postgres (not the file on disk)
and that the exact precision-fixed scores round-trip through the live DB query:

```
[serve_local] sourced 87493 bytes from DB for lululemon (score=4.30, company=lululemon athletica)
[serve_local] sourced 116989 bytes from DB for jbl (score=1.93, company=JBL)
[serve_local] sourced 111830 bytes from DB for nike (score=4.32, company=Nike)
```

Migration re-run a second time to confirm idempotency: rowcounts identical (accounts=17, audits=18,
module_executions=180) with no duplicates, round-trip still 18/18 PASS.
