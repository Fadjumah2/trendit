# Trendit — Functionality Test Plan

This file is a working checklist to prove the Trendit backend actually *functions*,
not just boots. Render logs confirm the server starts and `/health` returns 200 —
that only proves uptime. The tests below verify real functionality, in order from
infra up to the full agent loop. Work through them one at a time, top to bottom.
Do not skip ahead — each test assumes the ones above it pass.

Update the checkbox and add a one-line result note under each test as it's completed.

---

## 1. Basic server health
- [ ] `curl https://trendit-4ocu.onrender.com/health` returns `200 OK`
- Result:

## 2. Database connectivity
- [ ] Hit a route that reads/writes to the "Trendit DB" Postgres instance
  (e.g. a `/customers` list route, or a lightweight admin/debug endpoint if one exists —
  create a minimal one if it doesn't yet)
- [ ] Confirm it returns real data (or an empty-but-valid result) instead of erroring
- Result:

## 3. OAuth → gbp_credentials write
- [ ] Run the website's existing "connect profile" OAuth flow against a real/test GBP location
- [ ] Query Postgres directly: `SELECT * FROM gbp_credentials WHERE customer_id = '<test_id>';`
- [ ] Confirm a row exists with encrypted tokens (this is still an open checkbox in
  Phase 1 of the roadmap — confirm it's actually wired before trusting anything downstream)
- Result:

## 4. Token refresh
- [ ] Force/simulate an expired token for the test customer
- [ ] Confirm the backend refreshes it automatically without erroring
- [ ] Confirm the refreshed token is written back to `gbp_credentials`
- Result:

## 5. MCP server tools directly (bypass the agent)
- [ ] Run `tests/manual_test_email_approval.py` or an equivalent manual script
- [ ] Call `get_local_posts` and `create_local_post` directly against a real GBP
  listing using `GOOGLE_REFRESH_TOKEN` (dev-only — never used on the real
  customer-facing publish path)
- [ ] Confirm the forked MCP server + Postgres token storage work end-to-end
- Result:

## 6. Email approval loop
- [ ] Insert a fake draft into `post_history`
- [ ] Trigger `notify.send_draft_for_approval(post_id)`
- [ ] Receive the real email via Resend
- [ ] Click Approve → confirm it hits `publish_post`
- [ ] Expected: this should fail *only* due to missing `gbp_credentials` for the
  test location if Test 3 hasn't been completed yet — any other failure is a real bug
- Result:

## 7. Full agent draft (Phase 3 dependent)
- [ ] Trigger the ADK `LlmAgent` to draft a Standard post
- [ ] Confirm the deterministic validator runs on the draft (char limits, CTA enum,
  required fields, etc.)
- [ ] Confirm a valid draft reaches the email approval step
- Note: Phase 3 (agent + validator + pipeline wiring) may still have unchecked
  items on the roadmap — if so, this test isn't runnable yet, and that's expected,
  not a bug in what's currently live.
- Result:

## 8. True end-to-end ("north star")
- [ ] Real intake → agent drafts a Standard post → validator checks it → owner
  approves via email → real `create_local_post` call fires → post visibly appears
  on the real/test GBP listing
- Result:

---

**Instructions for coding assistant:** Work through tests 1–8 in order. For each one,
run the described check, report the actual result (success/failure + error output if
any), and update this file's checkbox and Result line before moving to the next test.
Stop and flag clearly if a test fails for a reason other than the expected/known
gaps noted above...
