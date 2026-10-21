## 1. Prompt sequence

### P01 — Requirements extraction and evaluation mapping

```text
Read both the Common Instructions and Evaluation Criteria PDF and the Problem 4 statement. Extract every mandatory deliverable, functional requirement, validation, business rule, quality criterion, submission format, and deadline into a traceability matrix.
Columns: ID, requirement, source quotation/page, priority (mandatory/core/stretch), implementing component, test ID, completion evidence, status.
Distinguish exact requirements from assumptions. Identify conflicting or missing information. Create docs/requirements-matrix.md and a short MVP checklist. Do not start coding yet.
```

**Acceptance evidence:** Source-backed requirements matrix; documented unknowns; no invented PDF content.

### P02 — Resolve calculation and workflow ambiguities

```text
Audit the problem for unspecified behavior. Specifically examine:
- Interpretation of "every full 1% above threshold" (e.g., threshold 12%, observed 12.99%, 13%, 14.99%).
- Whether moisture equal to max accepted is valid, and whether a crop can omit max accepted.
- Order and precision of rounding for percentage, deducted kg, net kg, price, and money.
- Price-list tie handling for multiple entries on the same effective_from date.
- Whether amount is computed using net kg * per-kg price and when rounding occurs.
- Whether a delivered_on date can precede advance/payment records.
- Week identification, eligibility for Draft vs Finalised payouts, and Paid transition rules.
- Whether credit/debit notes are mandatory to build and how they affect next payout.
For each, show known rule, risk, proposed implementation assumption, and targeted test. Ask only genuinely blocking questions; add approved or reasonable clearly labelled assumptions to README and docs/decisions.md.
```

**Acceptance evidence:** Decision log with boundary examples, including no retrospective changes.

### P03 — Architecture, technology stack, and delivery plan

```text
Propose a hackathon-friendly architecture for an API + relational database + web UI + hosted deployment. Prefer a stack our team can build and demo reliably [INSERT PREFERRED STACK OR REQUEST TWO OPTIONS]. Compare setup time, testability, decimal support, deployment simplicity, and time-to-demo. Then select one based on our approval.
Provide component diagram, request/data flows, directory structure, environment configuration, local commands, milestone order, and an MVP-first task board. Clearly separate mandatory functionality from stretch scope. Do not write implementation code until the stack is selected.
```

**Acceptance evidence:** Approved stack, diagram, implementation sequence, run/deploy plan.

### P04 — Database schema and migration design

```text
Design the relational schema and executable migrations for Farmer, Crop, allowed CropGrade, effective-dated PriceList, Delivery (immutable calculation snapshot), Advance, Payout, PayoutDelivery association, and CreditDebitNote (if correction feature is in MVP).
Specify foreign keys, unique constraints, indexes for crop/grade/effective_from and farmer/week, check constraints for positive quantities and enum states, and concurrency control approach. Do not collapse historic prices into one editable field. Include an ER diagram and explain transaction boundaries. Generate migrations and schema tests only after review.
```

**Acceptance evidence:** Applied migrations and enforced database invariants.

### P05 — Domain calculation engine

```text
Implement isolated, pure, deterministic functions (or a dedicated domain service) to:
1) select effective dated prices at delivery date;
2) validate grade, positive weight/moisture and configured max;
3) calculate full percentage points above threshold, deduction percentage, deducted kg, net kg, and amount;
4) apply consistent Decimal precision and explicit rounding;
5) determine Monday–Sunday payout week and min(outstanding_advance, 30% of gross).
Return a complete calculation breakdown, not only an amount. Test boundary examples, large values, negative/zero inputs, and decimal precision. Do not update persistent data in these pure functions.
```

**Acceptance evidence:** Standalone passing tests with expected numerical results.

### P06 — Farmer, crop, price-list, and advance APIs

```text
Implement documented CRUD or appropriate safe management endpoints for farmers and crops, allowed grades, effective-dated price entries, and farmer advances. Preserve price-list history; do not overwrite old prices. Validate input on the server and use consistent response envelopes or documented schemas and distinct error codes (VALIDATION_ERROR, NOT_FOUND, CONFLICT, etc.). Add migration-backed persistence, sample requests/responses, and API integration tests.
Clarify how deletes or deactivation should work where records have downstream references; avoid destructive cascade of financial history.
```

**Acceptance evidence:** API calls persist across restarts; price history remains queryable.

### P07 — Delivery creation with frozen breakdown

```text
Build POST delivery and list/detail endpoints. During creation, find the latest effective price whose crop and grade match and effective_from is on/before delivered_on; reject with an informative missing-price error otherwise. Validate all supplied fields and save the complete calculation snapshot atomically, including selected price and source price-list ID. Return breakdown: grossKg, moisturePercent, deductionPercent, deductionKg, netKg, appliedPricePerKg, amount, and deliveredOn.
Ensure later price edits/additions do not alter saved deliveries. Prevent editing deliveries included in Finalised payouts; design the correction-note path. Add tests for exact effective dates, wrong crop/grade, concurrent input, and historical immutability.
```

**Acceptance evidence:** Stored delivery matches preview and does not change after price updates.

### P08 — Weekly payout generation and lifecycle

```text
Implement generation of a farmer's Monday–Sunday weekly payout from eligible deliveries not already included in another payout. Calculate gross from persisted delivery amounts, never by recomputing prices. Handle zero deliveries explicitly and avoid duplicate/overlapping payouts.
Support Draft -> Finalised -> Paid with documented allowed transitions. At Finalisation, deduct min(current outstanding advance, 30% of gross), persist the exact deduction and net, and atomically update the advance balance. Finalised payout and its included deliveries must be immutable. Use a transaction and suitable locks/optimistic version checks so concurrent Finalisation cannot over-recover advances or double-include a delivery. Add repeat-request and race-condition tests.
```

**Acceptance evidence:** Payout totals reconcile; outstanding advance changes exactly once.

### P09 — Corrections and farmer ledger

```text
Implement a farmer ledger that reconciles delivery earnings, advances issued, advance recoveries, payouts, and credit/debit corrections. For a delivery in a Finalised payout, do not update or delete the original. Create a credit/debit note referencing the original delivery, with reason, amount, creation time, and clear sign convention, and apply it only in the next eligible payout.
Specify how a correction affects gross and whether advance recovery caps are calculated on adjusted payout amounts; flag this as an explicit business assumption if not stated. Provide deterministic ordering, opening/closing balance logic, and integration tests that reconcile ledger entries to payout totals.
```

**Acceptance evidence:** Immutable finalised records and traceable financial adjustments.

### P10 — UI: delivery entry and live calculation preview

```text
Create a responsive, accessible delivery-entry form. Include farmer selection, crop and allowed-grade selection, gross weight, moisture, delivery date, and clear field-level errors. Preview the exact computation before saving: applied price and effective date, moisture excess/full percent points, deduction %, deducted kg, net kg, and final amount. Fetch preview from the shared backend calculation service or apply identical verified logic, so UI and server cannot diverge.
Disable invalid submissions; show actionable missing-price errors and success results with saved delivery ID. Add component tests and a mobile layout review.
```

**Acceptance evidence:** Live preview matches stored API breakdown for edge cases.

### P11 — UI: price history, payouts, and farmer ledger

```text
Build a price-list screen filtered by crop/grade with chronological price history and effective dates; do not present earlier prices as overwritten. Build weekly payout list, payout detail/statement, and explicit Draft/Finalised/Paid controls with confirmations and disabled invalid transitions. Show farmer, week range, all included deliveries, each frozen breakdown, gross, advance recovery, net, and payout status. Build a searchable farmer ledger with advances, payouts, and corrections.
Use accessible tables, empty states, loading/error feedback, unambiguous currency/units, and tested calculations.
```

**Acceptance evidence:** A reviewer can follow one delivery through payout to farmer ledger.

### P12 — Robust input errors, logging, and API documentation

```text
Add a centralized error handler with stable machine-readable error codes and useful end-user messages. Distinguish validation, missing effective price, unsupported grade, over-max moisture, future date, already-assigned delivery, invalid payout transition, finalised-record mutation, and concurrency conflicts. Add request IDs and structured logs around price selection, delivery calculation, payout finalisation, and advance recovery; redact personal/bank reference values.
Generate OpenAPI documentation (or an equivalent API contract) with requests, responses, error cases, and example payloads. Review CORS, secrets handling, and basic access control appropriate to the rubric.
```

**Acceptance evidence:** Documented errors, log traceability, no exposed credentials.

### P13 — Business-rule and boundary test suite

```text
Write a parameterized business-rule test suite using the requirements matrix. Include at least:
- Price effective_from exactly equals delivered_on; nearest earlier selected; future-only price rejected; later list does not reprice old delivery.
- Moisture exactly at threshold; threshold + 0.99; threshold + 1.00; 14.99% in a meaningful crop configuration; max accepted exactly; above max rejected.
- Zero/negative gross kg and moisture; unsupported grade; future delivery date.
- Two deliveries of same farmer/week; duplicate payout request; no eligible deliveries; Monday and Sunday boundaries.
- Outstanding advance < cap, = cap, > cap, and zero; finalising same payout twice; two payouts finalised concurrently.
- Attempt to edit a delivery linked to Finalised payout; correction in next payout only.
- Rounding with decimal weights/prices; gross - recovery + correction adjustments = net as defined; sum of delivery breakdowns reconciles to payout.
Use deterministic fixtures, explicit expected numbers, and record failures and fixes. Do not mark tests passing unless executed.
```

**Acceptance evidence:** Repeatable green unit/integration suite plus edge-case coverage matrix.

### P14 — End-to-end demonstration scenario

```text
Prepare a self-contained seed script and automated/manual E2E walkthrough:
1) Create farmer and crop with grades and moisture limits.
2) Add two different effective-dated prices for one crop/grade.
3) Issue a farmer advance.
4) Create deliveries on dates selecting different historic prices, including one with moisture deduction.
5) Display immutable breakdowns and historic price list.
6) Create and Finalise weekly payout, showing 30% cap and updated outstanding advance; mark Paid.
7) Try an invalid grade/missing price and show distinct errors.
8) Demonstrate historical immutability and a next-payout correction note if supported.
Provide expected arithmetic for each scripted input, a 3–5 minute demo narration, and a reset command. Never fabricate screenshots or actual test results.
```

**Acceptance evidence:** Seeded demo reproducible on clean install.

### P15 — Deployment, persistence, and smoke verification

```text
Configure a production-like hosted deployment for the approved stack, including environment variables, persistent relational database, migrations, build commands, basic health endpoint, and safe CORS. Produce a step-by-step deployment guide without hardcoded secrets. After deployment, perform smoke checks of UI loading, health endpoint, DB writes/readbacks, delivery breakdown, payout finalisation, historical price lookup, and restart persistence.
Return the deployed URLs and commands only after they have been verified. If you lack deployment access, provide precise operator steps and mark verification PENDING.
```

**Acceptance evidence:** Reachable hosted UI/API, migration success, persistent stored records.

### P16 — README, rubric review, and submission packaging

```text
Audit the repository against docs/requirements-matrix.md and the actual Common Instructions and Evaluation Criteria PDF. Build a line-by-line evidence table linking each completed requirement to route, screen, source file, test, or deployed demonstration. Identify gaps without hiding them.
Write README.md covering overview, architecture, stack and rationale, features, schema, setup commands, environment variables, migrations, running tests, API docs, demo data, deployed links (if verified), known limitations, and every assumption. Produce the submission files and names exactly as required by the Common Instructions PDF. Remove placeholders and never claim a feature or test passes without proof.
```

**Acceptance evidence:** Reproducible README, evidence-linked rubric checklist, submission-ready repo.

---

## 2. Final evaluation rehearsal prompt

```text
Act as a strict hackathon judge and senior QA lead. Inspect the current implementation, README, requirements matrix, test output, database migrations, and verified deployed app. Score only against the real Common Instructions/Evaluation Criteria document and Problem 4 requirements, never a fabricated rubric. Prioritize correctness under invalid input and concurrent requests, financial reconciliation, frozen history, modular architecture, reliable persistence, UI clarity, and demonstrable deployment.
Produce: (1) evidence-backed pass/fail matrix, (2) critical defects ranked by severity, (3) a prioritized minimal fix plan, (4) demo questions a judge may ask, (5) clearly identified unverified criteria. Where evidence is absent, mark NOT VERIFIED rather than PASS.
```
