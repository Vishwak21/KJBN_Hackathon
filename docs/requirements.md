# Problem 4 requirements

Milestones: M0 scaffold; M1 schema/seed/test specifications; M2 rules and tests; M3 API; M4 UI; M5 deployment; M6 documentation and final tag.

Core: manage farmers/crops/append-only price history/advances; delivery preview/create/edit with frozen calculations; weekly draft/finalise/paid payouts; correction notes; farmer ledger.

## Assumptions
1. Business dates are IST; audit timestamps UTC. X-Test-Clock requires an aware timestamp and explicit ALLOW_TEST_CLOCK opt-in.
2. Weights have 3 decimal places; moisture 2; prices/money 2. Reject excess precision; use Decimal and money half-up. Recovery cap rounds down to never exceed 30%.
3. One draft per farmer/week; later payouts allowed for new unassigned deliveries. Empty payouts rejected. Draft regeneration includes new deliveries and recomputes recovery.
4. Finalisation recalculates recovery atomically. Drafts do not reserve advances. Outstanding equals advances less finalised/paid recoveries.
5. Corrections are signed amount adjustment deliveries with a reason referencing a finalised/paid original. Date must be after the original payout week. Negative gross payouts have zero advance recovery.
6. Deliveries editable only while unassigned. Corrections immutable. Crop rules immutable. Price entries append-only and unique per crop/grade/date.
7. SQLite BEGIN IMMEDIATE serialises writes against double recovery and assignment. Paid changes status/audit time only.
8. Authentication omitted for an invented-data reviewer demo.

## Boundary test plan
Effective-date equality and missing price; moisture threshold, 14.99, 17.6, cap and maximum; half-up rounding; bad grade, nonpositive inputs, future delivery; frozen prices after backdated entry; several recoveries; empty weeks; Monday/Sunday boundaries; finalised immutability/corrections; concurrent requests; malformed API input.

The PDFs specify deliverables; they are not instructions to email anyone or fabricate deployment/commit evidence.
