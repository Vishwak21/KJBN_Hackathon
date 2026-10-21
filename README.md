# 1. Title and one-liner

**Harvest Ledger — Problem 4: Produce Procurement & Payout.** A buying-centre application that explains each delivery's price, moisture deduction, advance recovery and weekly payout.

## 2. Live links

Repository: [Vishwak21/KJBN_Hackathon](https://github.com/Vishwak21/KJBN_Hackathon). [Verified CI run](https://github.com/Vishwak21/KJBN_Hackathon/actions/runs/39545885776). Public UI and API URLs are **pending deployment**. There are no test credentials: authentication is intentionally omitted for this invented-data demo. Do not submit this README as a completed hosted assignment yet.

Local development: UI `http://localhost:5173`, API `http://localhost:8000`, Swagger `http://localhost:8000/docs`. Docker: UI `http://localhost:8080`.

## 3. Tech stack

| Layer | Choice |
| --- | --- |
| Backend | Python 3.12, FastAPI, Pydantic, Uvicorn |
| Persistence | SQLite, parameterised SQL, schema committed in `backend/schema.sql` |
| Frontend | React 19, TypeScript 5.8, Vite 6.4 |
| Verification | pytest, coverage.py, Ruff, Playwright, Prettier |
| Hosting | Docker Compose for local operation; prepared PythonAnywhere ASGI deployment, not yet exercised on an account |

All application choices use the recommended technologies. SQLite keeps clean-clone setup small; its single-writer limit is a deliberate tradeoff.

## 4. Architecture

```text
React forms ── JSON /api ──> FastAPI routes + input schemas
                                  │
                         services.py use cases
                                  │
                    rules.py: exact Decimal arithmetic
                                  │
                    db.py: request-scoped transactions
                                  │
                    SQLite: immutable price history,
                    frozen deliveries and payout membership
```

- `backend/`: routes, input contracts, rules, use cases, persistence, schema, seed and tests. Pure calculations are in `rules.py`; transactional decisions are in `services.py`, so direct API calls cannot bypass them.
- `frontend/`: API client, delivery/price screens, payout/ledger screens, styles and browser tests.
- `scripts/`: coverage, deployment packaging and provider registration/start commands.
- `deploy/`: provider-specific configuration.
- `docs/`: requirement interpretation and reviewer checklist.
- `.github/`: CI checks on pushes and pull requests; check the repository Actions tab for remote results.

Each request owns its connection. Reads use a deferred transaction; writes use `BEGIN IMMEDIATE`. Write decisions and inserts/updates commit together. SQLite thread affinity is disabled because FastAPI may move a request between worker threads; connections are never shared across requests.

## 5. Running locally

Prerequisites: Python **3.12**, Node.js **24**, npm, Git. Docker Compose v2 is optional. Run commands from the repository root.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend/requirements.txt
npm.cmd ci --prefix frontend
python -m backend.seed
python -m uvicorn backend.api:app --reload
```

In another terminal at the repository root:

```powershell
npm.cmd run dev --prefix frontend
```

Open `http://localhost:5173`. Vite proxies `/api` to the backend; no environment setup is required for this local arrangement. On Linux/macOS, activate with `source .venv/bin/activate` and use `npm` instead of `npm.cmd`.

One-command container equivalent:

```sh
docker compose up --build
```

Open `http://localhost:8080`. SQLite is stored in the named `procurement_data` volume and survives container replacement. `docker compose down` retains it.

`.env.example` describes configuration; Python does **not** automatically load that file. Export variables in your shell or set them through your host:

| Variable | Default / use |
| --- | --- |
| `DATABASE_PATH` | `./data/procurement.db`; writable SQLite path |
| `CORS_ORIGINS` | `http://localhost:5173`; comma-separated exact allowed UI origins |
| `ALLOW_TEST_CLOCK` | `false`; opt in to reviewer date overrides |
| `VITE_API_BASE_URL` | Empty: same-origin requests; set at frontend build time for a separately hosted API |
| `STATIC_DIR` | Unset; set to the built `frontend/dist` directory to serve UI and API from FastAPI |
| `PYTHONANYWHERE_USERNAME`, `PYTHONANYWHERE_API_TOKEN`, `PYTHONANYWHERE_HOST` | Only needed by the optional publishing script; never commit tokens |

For a separate UI/API origin, set `VITE_API_BASE_URL` in the UI shell before `npm run build`, and include the UI origin in backend `CORS_ORIGINS`.

The seed command applies the initial schema and inserts invented farmers, three crops, grade prices, an advance, deliveries, a paid statement and a correction note. It does nothing if farmers already exist. It never deletes reviewer work.

## 5a. Deployment

**Prepared, not publicly deployed or provider-tested.** Docker is also not installed in the current development environment, so the images/Compose configuration have not been run here.

PythonAnywhere is the prepared free-account path. Its ASGI feature is experimental; verify that the selected account supports it before publishing. Its [ASGI API documentation](https://help.pythonanywhere.com/pages/ASGIAPI/) describes account registration and socket startup. [Free account limits](https://help.pythonanywhere.com/pages/FreeAccountsFeatures/) include disk and app-expiry limits. Do not assume a service will stay available without renewing it for the review period.

1. Create the public GitHub/GitLab repository and push the milestone history.
2. Run `python scripts/package_deployment.py`. It installs locked frontend dependencies, builds the UI and creates `deployment-bundle.zip` from tracked sources plus built assets. The zip is ignored by Git.
3. In the provider dashboard, upload that zip, open a Bash console, and extract it into `/home/USERNAME/harvest-ledger`. These are manual steps.
4. In that directory, run:
   ```sh
   python3.12 -m venv .venv
   .venv/bin/python -m pip install -r backend/requirements.txt
   .venv/bin/python -m backend.seed
   ```
5. Generate a provider API token in the dashboard. In a trusted shell with this repository, set the three `PYTHONANYWHERE_*` variables. Run `python scripts/deploy_pythonanywhere.py` only when ready to create the public app. `deploy/pythonanywhere.json` supplies the registration template.
6. The provider runs `scripts/pythonanywhere-start.sh`; it migrates/seeds idempotently, enables built static assets, and starts Uvicorn on the provider socket. The reviewer clock remains disabled unless explicitly enabled in that environment.
7. Check HTTPS `/`, `/health`, `/docs`, delivery preview/save, history, finalise/pay and ledger. Fill section 2 with the actual URLs and confirm provider renewal dates.
8. To redeploy, build/upload/extract the new package without replacing `data/` or `.venv/`, then run `python scripts/deploy_pythonanywhere.py --reload`. To seed again, run `.venv/bin/python -m backend.seed`; existing data is retained.

For a fresh demo, select a new empty `DATABASE_PATH` and run the seed command. Back up an existing database before changing it. No destructive reset endpoint is exposed.

## 6. Running tests and coverage

From an activated Python environment:

```sh
python scripts/coverage.py
```

This runs all backend unit/API/concurrency tests and writes `coverage.txt` and `coverage.json`. See [verification evidence](docs/verification.md) for completed local checks. The latest measured backend line coverage is **97% overall**, **100% for rules.py** and **100% for services.py**. Reports include the browser-server launcher, which runs outside pytest. Coverage is line coverage; no branch-coverage claim is made.

Rules tested include effective-price boundaries, fractional moisture, maximum rejection, deduction cap, half-up rounding, invalid numbers/grades/dates, frozen historical deliveries, repeated recovery, draft regeneration, empty weeks, correction restrictions, status transitions, concurrent generation/finalisation and parallel HTTP requests. API tests distinguish malformed requests, missing resources, conflicts, unavailable databases and unexpected errors.

Frontend checks:

```sh
npm run lint --prefix frontend
npm run format:check --prefix frontend
npm run build --prefix frontend
npm run test:e2e --prefix frontend
```

Browser tests start isolated API/UI servers and use temporary databases. Free ports 8000 and 5173 first. Locally they use installed Microsoft Edge. For another platform, install Playwright Chromium with `npx --prefix frontend playwright install chromium` and set `CI=true` before running. CI uses Chromium. Browser coverage includes delivery preview/save, payout finalisation/payment, ledger, history and phone viewport overflow. Provider availability, Docker execution and visual checks on real phones are not covered.

Backend formatting/lint:

```sh
python -m ruff check backend scripts
python -m ruff format --check backend scripts
```

## 7. API overview

Exact request contracts: `/docs`; JSON schema: `/openapi.json`. Decimal measurements and money are **JSON strings**, IDs are integers, dates are `YYYY-MM-DD`. Unknown input fields are rejected.

| Method | Path | Purpose | Main errors |
| --- | --- | --- | --- |
| GET | `/health` | Database health and UTC timestamp | 503 |
| GET / POST | `/api/farmers` | Paginated farmers / create | 422 |
| PUT | `/api/farmers/{id}` | Update contact/bank reference | 404, 422 |
| GET / POST | `/api/crops` | List / create immutable quality rules | 409, 422 |
| GET / POST | `/api/prices` | Filtered history / append an entry | 404, 409, 422 |
| POST | `/api/advances` | Add an advance | 404, 422 |
| POST | `/api/deliveries/preview` | Calculate without saving | 404, 422 |
| POST | `/api/deliveries` | Save frozen breakdown | 404, 422 |
| PUT | `/api/deliveries/{id}` | Edit an unassigned regular delivery | 404, 409, 422 |
| POST | `/api/deliveries/{id}/corrections` | Signed correction referencing the original | 404, 409, 422 |
| GET / POST | `/api/payouts` | Paginated history / generate or refresh draft | 404, 409, 422 |
| GET | `/api/payouts/{id}` | Statement including every delivery | 404 |
| POST | `/api/payouts/{id}/finalise` | Freeze amounts and apply recovery | 404, 409 |
| POST | `/api/payouts/{id}/pay` | Mark a finalised statement paid | 404, 409 |
| GET | `/api/farmers/{id}/ledger` | Deliveries, advances, payouts, balance | 404, 422 |

Farmer, price, payout and ledger pages support `limit` (1–500) and `offset`. Price filters: `crop_id`, `grade`; payouts: `farmer_id`. Ledger pagination applies the same offset independently to its three lists. Money-changing operations are POST/PUT only.

## 8. Business rules and assumptions

| PDF rule | Enforcement | Tests |
| --- | --- | --- |
| 1. Latest price effective on/before delivery | `services.preview_delivery` | `test_freeze_price_and_exact_effective_date`, `test_missing_price_names_combination` |
| 2. Full moisture points, 10% cap, maximum acceptance | `rules.breakdown` | `test_moisture_boundaries`, `test_max_rejection` |
| 3. Frozen breakdown and half-up amount | `rules.breakdown`, `services.create_delivery` | `test_half_up`, `test_freeze_price_and_exact_effective_date` |
| 4. Monday–Sunday and unique membership | `rules.week_start`, `services.generate_payout`, schema | `test_dates`, `test_new_deliveries_join_draft_and_later_payout`, `test_concurrent_generation_has_one_draft_and_no_duplicate_membership` |
| 5. Lesser of outstanding/30%; recover only at finalisation | `rules.payout_totals`, `services.finalise_payout` | `test_repeated_recovery_and_status_transitions`, `test_two_drafts_recompute_against_remaining_balance` |
| 6. Finalised financial immutability; linked later correction | `services.edit_delivery/create_correction/finalise_payout/pay_payout` | `test_empty_week_and_edit_lock`, `test_correction_rejections_and_edit_immutability` |
| 7. Allowed grade, positive weight/moisture, no future delivery | schemas, `rules.decimal_value/business_date`, services | `test_bad_delivery`, `test_invalid_numbers`, `test_malformed_requests` |

Numbered assumptions:

1. A business date means an IST calendar date. Audit timestamps are stored in UTC and shown in IST.
2. Input weight permits three decimal places; moisture, price and money permit two. Inputs are bounded to one billion per measurement. Exact weight parts are retained without intermediate rounding. Decimal amounts are strings in JSON and SQLite; money display also formats strings without floating-point conversion.
3. Gross payout is the sum of already-rounded delivery amounts. The recovery cap rounds **down** to a paise so recovery never exceeds 30%; net equals gross minus recovery exactly.
4. Empty weeks return 409. One draft per farmer/week reserves its deliveries. Regenerating it includes new unassigned deliveries. New deliveries after finalisation can enter another payout for the same week.
5. Outstanding is derived from all advances less finalised/paid recoveries. Draft recovery is indicative and recalculated under the write lock during finalisation. Given-on is informational; creating a backdated advance affects the current balance, not historic frozen payouts.
6. Regular deliveries can be edited only while unassigned. Draft-assigned deliveries are reserved and also locked. Corrections are immutable signed money adjustments with a reason and a reference to a regular delivery in a finalised/paid payout.
7. A correction's date must be after the original payout's Sunday and cannot be future. It enters the payout for its own week; negative gross payouts have zero advance recovery. Multiple correction notes are permitted and form the audit trail.
8. Price entries are append-only and unique per crop/grade/effective date; a second price on the same effective date is rejected. Crop quality rules/grade sets are immutable; create a distinct crop for changed rules.
9. Paid changes only status and payment timestamp. Finalised financial values, recovery and memberships remain frozen. Duplicate finalise/pay requests return 409.
10. No authentication or real personal data is included. All seed phone/bank references are visibly invented.

## 9. Error handling and logging

All errors use:

```json
{"error":{"code":"invalid_grade","message":"Allowed grades: A,B,C.","details":[],"request_id":"..."}}
```

Validation/domain input errors: 422; missing resources: 404; duplicates/invalid state: 409; disabled clock: 403; database availability failures: 503; unexpected exceptions: sanitised 500. Stack traces and request bodies are not returned to clients. Transactions roll back failures.

Structured JSON logs include UTC timestamp, severity, event, request ID, method/path, response status and duration. Paths identify delivery/payout/farmer IDs without logging names, phone numbers or bank details. Rule violations/constraint conflicts log WARNING; database/unexpected failures log ERROR (including exception type for unexpected failures). Validation responses identify fields without echoing their values. `X-Request-ID` is generated by the server and returned on responses.

Logs appear in the terminal, `docker compose logs backend`, or the provider's app error log after deployment. The provider log location still needs account-side confirmation.

## 10. Reviewer aids

To opt into the clock override locally in PowerShell, **before** starting the API:

```powershell
$env:ALLOW_TEST_CLOCK="true"
python -m uvicorn backend.api:app
```

Send `X-Test-Clock: 2026-10-19T12:00:00+05:30` with delivery preview/create/edit, advance creation or correction creation. An explicit timezone is required. The timestamp is converted to IST and only changes date validation; it does not change audit timestamps or advance balances. The header is rejected when disabled. No clock setting is stored globally.

Example preview (PowerShell):

```powershell
$body = '{"farmer_id":1,"crop_id":1,"grade":"A","gross_kg":"100","moisture":"17.6","delivered_on":"2026-10-12"}'
Invoke-RestMethod http://localhost:8000/api/deliveries/preview -Method Post -ContentType application/json -Body $body
```

Expected maize breakdown at seeded price: 100 kg gross − 3 kg moisture deduction = 97 kg net; ₹25/kg; ₹2,425.00. On an unmodified fresh seeded database, Farmer A has ₹4,250 outstanding after a prior paid payout; a current-week credit/debit note demonstrates correction handling.

Use `docs/reviewer-checklist.md` to verify all PDF edge cases. Re-seed instructions are in section 5a. Swagger supports direct API review without the UI.

## 11. Known limitations

- Hosted URLs are still pending. M5 hosting, hosted edge-case review, final documentation sign-off and the `v1.0` tag remain pending.
- Provider ASGI configuration is prepared from official documentation but has not been exercised on an account. Docker is not available in the development environment, so container startup has not been verified.
- Authentication, multi-centre support, printable PDF statements and quality bonuses are omitted. All mandatory calculation flows are prioritised.
- SQLite is appropriate for one small buying centre; it serialises writes and does not support horizontally distributed writers. There is no automatic backup/restore workflow.
- No idempotency keys for delivery/advance/note creation. Do not blindly retry an uncertain write; check the ledger first.
- The UI's farmer chooser loads at most 500 farmers. Crop listing is unpaginated. No deletion or draft-cancellation flow is offered.
- Schema setup is idempotent initial SQL, not a versioned migration framework. Frontend responses currently use a shared flexible row type rather than generated OpenAPI types.
- Browser tests cover the core happy path and a mobile viewport, not every form or actual device. Amount/validation/concurrency boundaries are primarily backend tests.

## 12. AI and third-party usage

Codex assisted requirement analysis, implementation, tests, debugging and documentation. The prompt history is in [PROMPTS.md](PROMPTS.md). The submitter must review, understand and be able to modify every generated line before submitting; this is not a claim that the submitter independently wrote or verified it.

No low-code builder, CRUD generator or copied project was used. Third-party packages are declared in `backend/requirements.txt`, `frontend/package.json` and its lockfile. UI styles are local; no external images/fonts are required. The final personal self-assessment and write-up need the submitter's review.
