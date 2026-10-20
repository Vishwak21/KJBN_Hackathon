# Reviewer checklist

These are checks to perform, not claims of hosted verification. All hosted boxes remain unchecked until a public deployment exists.

## PDF edge cases

- [ ] Effective date equality: append a maize/A price, deliver on that exact date, verify its price entry ID.
- [ ] Missing crop/grade price: use a date before the earliest matching price; expect a named combination and 422.
- [ ] Maize moisture 14% and 14.99%: both 0% deduction.
- [ ] Maize moisture 17.6%: 3% deduction; 100 kg becomes 97 kg.
- [ ] Moisture at maximum 28%: accepted with 10% deduction; 28.01%: rejected.
- [ ] Grade Z, zero/negative weight or moisture, future delivery: reject through API as well as UI.
- [ ] Enter multiple weekly deliveries and a large advance: each finalisation recovers no more than 30%; draft generation does not change the balance.
- [ ] Add a backdated price after a delivery exists: the old delivery retains price ID and amount.
- [ ] Empty week: 409 with actionable message.
- [ ] Monday and Sunday deliveries belong to the same weekly statement; the following Monday does not.
- [ ] Decimal weights: gross kg equals deduction kg plus net kg; payout gross equals sum of delivery amounts; net plus recovery equals gross.
- [ ] Finalise twice / mark paid before finalise: 409; no second recovery.
- [ ] Edit a finalised delivery: reject; create a signed correction in a later week; verify original reference and next statement.
- [ ] Concurrent generation/finalisation: no duplicate memberships or advance recovery.

## Submission

- [ ] Public repository contains M0–M6 progress; actual hashes in SUBMISSION.md.
- [ ] Public UI/API/docs/health reachable with invented seed data.
- [ ] Hosting remains active throughout review; renewal/cold-start behaviour documented.
- [ ] Run clean-clone installation, coverage and browser checks.
- [ ] CI has passed on the public repository.
- [ ] Personally review generated code and self-assessment.
- [ ] Complete SUBMISSION.md and create final v1.0 tag only after all required deliverables pass.
- [ ] Reply to the assignment email yourself with name/phone/problem number and links.

No email or external publication has been performed by the assistant.
