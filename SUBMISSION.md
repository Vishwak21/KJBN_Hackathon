## A. What I built

Harvest Ledger implements Problem 4, Produce Procurement & Payout, with a JSON API, SQLite persistence and a TypeScript web UI.
Core flows include farmers/crops, effective-price history, advances, delivery preview/save/edit, linked corrections, weekly payout generation/finalisation/payment and farmer ledgers.
The UI shows the weight-to-money calculation and statement arithmetic using the API.
Backend boundary/concurrency tests and the delivery-to-payment browser workflow pass.
The application is publicly hosted, and the participant confirmed review of this AI-assisted write-up on 2026-10-22.

## B. Three design decisions

**1. Decision:** use Decimal calculations and persist their exact string values. **Alternative considered:** integer paise throughout or floating-point calculations. **Why I chose this:** money needs paise, while weight deductions can have more than three decimal places; Decimal keeps gross, deduction and net weight consistent until the payable amount is rounded half-up. **What it cost me:** explicit input precision checks and string formatting at the API/UI boundary; there are no database-native decimal aggregation queries.

**2. Decision:** freeze each saved delivery's price ID and breakdown. **Alternative considered:** recalculate every ledger/statement from current price history. **Why I chose this:** appending a backdated price must not silently change a farmer's recorded purchase. A correction is a signed, explained note referencing a finalised original, dated in a subsequent week. **What it cost me:** duplicated historical values and a separate correction workflow; amendments require an audit trail rather than a convenient overwrite.

**3. Decision:** derive advance balance and serialise write use cases with SQLite transactions. **Alternative considered:** maintain a cached balance, or use PostgreSQL with row locks. **Why I chose this:** a derived balance has one financial source of truth; the write lock makes membership assignment and finalisation atomic, including two drafts competing for the same remaining advance. **What it cost me:** one writer at a time, bounded ledger aggregation work and no horizontal writer scaling.

## C. The hardest part

Browser verification exposed a SQLite connection-ownership issue that sequential API tests had missed. FastAPI can move a request's dependency/handler work across worker threads; SQLite's default thread restriction caused a server error and could leave later requests waiting on a lock. Commit `6570207` disables that restriction for request-owned connections, keeps writes atomic, and separates read transactions. A 30-request parallel HTTP regression test now passes alongside concurrent payout generation/finalisation checks. The UI milestone `e249e85` adds the real browser workflow and explicit accessible field names. This account describes observed debugging evidence, not a claim that the submitter personally performed every step.

## D. How I handle failure

| Failure | Response / state | Logs / UI |
| --- | --- | --- |
| Bad request | 422 with field details; no writes | UI shows actionable message; values are not echoed in logs |
| Domain violation | 404/409/422; transaction rollback | WARNING with request ID; UI preserves entered fields |
| Database availability failure | 503; rollback | ERROR and request ID; retry message |
| Unexpected exception | Sanitised 500; rollback | ERROR with exception type and request context; no client stack trace |

Server-generated `X-Request-ID` correlates the JSON response with structured logs.

## E. Milestone log

Dates are IST. Public deployment and participant documentation review are recorded; the final submission revision is identified by tag v1.0.

| Milestone | Date completed | Commit hash |
| --- | --- | --- |
| M0 - Scaffold | 2026-10-19 | `73f71be` |
| M1 - Domain model | 2026-10-19 | `01d128b` |
| M2 - Business rules | 2026-10-19 | `fea7a4b` |
| M3 - API | 2026-10-19; hardening 2026-10-21 | `d8fdcf7`, `6570207` |
| M4 - UI | 2026-10-21 | `e249e85` |
| M5 - Deployment | 2026-10-22 | `10b022b` |
| M6 - Documentation | 2026-10-22 | `0efea99` |

## F. If I had two more days

1. Replay every hosted write/edge-case flow and verify restart persistence before submission.
2. Add and exercise database backup/restore before any real financial use.
3. Add idempotency keys to money-changing creation endpoints to make network retries safe.
4. Generate typed frontend contracts from OpenAPI and split the largest screen components.
5. Expand browser coverage for corrections, price changes, error recovery and keyboard/mobile operation.

## G. Self-assessment

Conservative evidence-based scores, following participant review on 2026-10-22; unverified deployment checks remain disclosed.

| Rubric criterion | Score / 5 | Justification |
| --- | --- | --- |
| Business logic correctness | 4 | Core rules and concurrent recovery tested; assumptions documented |
| Code clarity and structure | 4 | API/rules/persistence separated; flexible UI response types remain |
| Error and exception handling | 4 | Consistent sanitised errors and rollback; limited retry UX |
| Logging and observability | 4 | Structured request/rule logs; hosted log access unverified |
| Data modelling and persistence | 4 | Frozen history, constraints, indexed relations; initial schema only |
| API design | 4 | Resource routes, pagination and OpenAPI; no idempotency keys |
| UI usability | 4 | Core browser flow and phone layout pass; broader usability untested |
| Testing | 4 | 57 backend tests, business modules 100% line coverage; branch coverage unmeasured |
| Deployment and operability | 2 | CI and hosted read-only checks pass; Docker/restart checks pending |
| Git hygiene | 3 | Milestone history retained; submission revision identified by v1.0 |
| Documentation and write-up | 3 | Required structures, live links and participant review recorded |
