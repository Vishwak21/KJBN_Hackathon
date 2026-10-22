# Local verification - 2026-10-21 (IST)

- Fresh project virtual environment installed from backend/requirements.txt.
- 57 backend tests passed in that environment; coverage: 97% overall, 100% rules.py and services.py line coverage.
- Two Playwright tests passed in headless Edge: real delivery-to-paid-payout/ledger/history workflow and 390px phone viewport.
- Ruff lint/format, Prettier format check and TypeScript type checking passed.
- Locked npm clean installation and production build passed; npm reported no known vulnerabilities at installation time.
- Production static-file configuration served the built HTML/JS, health, Swagger, seeded ledger and exact delivery preview successfully.
- Deployment zip was generated and inspected: source, required documentation, provider script and built UI included; environment secrets, database files and installed dependencies excluded.
- Docker execution was not verified. PythonAnywhere deployment was completed by the participant on 2026-10-21; public verification is recorded below.
- GitHub Actions passed for commit 71f7bcde633e43dc96b564a995157ecb2b75cd9e: https://github.com/Vishwak21/KJBN_Hackathon/actions/runs/39545885776 (verified after publication).


## Hosted verification - 2026-10-22 (IST)

Base URL: https://vishwak.pythonanywhere.com/

Verified against the public deployment without changing stored records:
- UI HTML and referenced JavaScript/CSS assets: HTTP 200.
- /health: HTTP 200, status ok.
- /docs and /openapi.json: HTTP 200.
- Seeded Farmer A ledger: 3 delivery/note records; outstanding advance 4250.00.
- Maize/A, 100 kg, seeded price 25.00/kg: moisture 14 and 14.99 -> 0% deduction, 2500.00; 17.6 -> 3%, 2425.00; maximum 28 -> 10%, 2250.00.
- Moisture 28.01, grade Z, zero weight and a pre-price date: HTTP 422 with the expected distinct domain codes.

The web browsing tool could not fetch this host, so direct HTTPS requests were used for verification. Local/CI browser tests remain separate evidence; a public UI interaction test is not claimed here.

Not yet verified: hosted create/finalise/pay/correction workflows, persistence across provider restart, account log access, expiry/renewal and the participant's personal reviewer checklist. The participant confirmed documentation review on 2026-10-22; the final submission revision is identified by v1.0.

Latest verified CI before final documentation-only changes: https://github.com/Vishwak21/KJBN_Hackathon/actions/runs/39781343580 (commit 10b022b7d8f70b29e24e0f45059878f8717c5503), completed successfully.
