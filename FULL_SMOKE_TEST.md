# Trendit — Full Smoke Test Prompt
*Covers every fix made this session: deploy, connect flow, no-GBP handling, onboarding wizard, first-draft trigger, approval loop, and the new daily cron trigger. Run in order — later tests depend on earlier ones succeeding.*

Hand this whole document to your coding assistant, or work through it yourself in Cloud Shell / the live site. Check off each item with the **actual observed result**, not just "looks right" — several bugs this session only showed up by checking the database directly (`/debug/db`), not just the UI.

---

## 0. Pre-flight

- [ ] Confirm the latest backend deploy on Render shows **"Live"**, not "Failed" (dashboard → `trendit` service → Events tab)
- [ ] Confirm the latest frontend deploy on Render shows **"Re
- [ ] Have two Google accounts ready to test with:
  - **Account A** — has an existing, verified Google Business Profile
  - **Account B** — has no Business Profile at all (or use a fresh Google account)
- [ ] Have access to the inbox for whatever email you'll type into the signup form (needs to actually receive mail)

---

## 1. Backend health
- [ ] `GET https://trendit-4ocu.onrender.com/health` → `{"status": "ok"}`
- [ ] `GET https://trendit-4ocu.onrender.com/debug/db` → `pool_initialized: true`, `query_success: true`, and lists all expected tables (`customers`, `gbp_credentials`, `business_content_profiles`, `post_history`, `telegram_chat_links`, `telegram_link_codes`)

---

## 2. Signup form (frontend)
- [ ] Visit `/signup` on the live site
- [ ] Confirm the form shows **only** Business Name + Email — no Industry/Tone/Focus fields (if you still see those, the old `signup.tsx` fix didn't land)
- [ ] Submit with a valid business name + real email → should show the "Almost there" screen with a "Connect Google Business Profile" button

---

## 3. OAuth connect — Account B (no GBP)
- [ ] Click "Connect Google Business Profile," sign in with **Account B**
- [ ] Expected: redirected to `/setup-gbp`, **not** to `/onboarding` and **not** to a generic error page
- [ ] Confirm the page shows the 3-step instructions and both buttons ("Create your Business Profile," "I already have one")
- [ ] Check `/debug/db` → `customers` row count should be **unchanged** — confirms no false customer/credential/email was created for this failed connection
- [ ] Confirm **no** "connected" email arrived for Account B's email address

## 4. OAuth connect — Account A (has GBP)
- [ ] Click "Connect Google Business Profile," sign in with **Account A**
- [ ] Expected: redirected to `/onboarding?connected=1&customer_id=...&location_id=...` (check the URL bar — if `location_id` is missing or blank, the backend response is missing that field)
- [ ] Check the email inbox for Account A → connection-confirmation email should arrive within ~30 seconds
- [ ] Check `/debug/db` → new row in `customers` (email matches Account A), new row in `gbp_credentials` with a real `location_id` (not `pending_location_discovery`)

---

## 5. Onboarding wizard
- [ ] On `/onboarding`, confirm it's the step-by-step wizard — one question per screen, tappable option cards, step counter ("Step X of Y") — **not** the old single-page form
- [ ] Walk through all steps: category → services → tone → target customer → promos → review
- [ ] Test the "Other" branch on category (should reveal a free-text follow-up)
- [ ] Test back button works and preserves previous answers
- [ ] On the review screen, submit
- [ ] Expected: redirected to `/dashboard`

## 6. First-draft trigger (onboarding completion)
- [ ] Check `/debug/db` → new row in `business_content_profiles` for this customer/location
- [ ] Check `/debug/db` → new row in `post_history` for this customer/location, `owner_decision = 'pending'`
- [ ] Check Account A's inbox → a **draft approval email** should arrive (separate from the earlier connection-confirmation email) within ~30-60 seconds of submitting the wizard
- [ ] Open the email, confirm the draft content looks reasonable for the business info entered and both Approve/Reject links are present

---

## 7. Approval loop
- [ ] Click **Reject** on a test draft → confirm the page shows a rejection confirmation, and `/debug/db` shows `owner_decision = 'skipped'` (or however your schema marks it) for that row
- [ ] Click the same Reject link again → should show "already [decision]," not process twice
- [ ] Generate a second draft (see Section 8 below to trigger one on demand), click **Approve**
  - If you have real GBP publish access: confirm it says "Approved and published!" with a reference ID, and the post actually appears on the real Google Business Profile listing
  - If not testing a real publish yet: confirm it fails gracefully with "Approved, but failed to publish to GBP: [error]" rather than crashing — and confirm `owner_decision` is still marked `approved` in the DB even though publish failed

---

## 8. Daily cron trigger (new this session)
- [ ] In GitHub, go to the backend repo's **Actions tab** → "Daily draft trigger" workflow → **Run workflow** (manual trigger, don't wait for the schedule)
- [ ] Confirm the run succeeds (green check), open the log, confirm it shows `HTTP 200` and a JSON body like `{"checked": N, "succeeded": N, "failed": 0, "results": [...]}`
- [ ] Confirm customers with a **pending** draft already sitting in their inbox were correctly **skipped** (should show up in `checked` count but not generate a duplicate)
- [ ] Confirm a customer with no pending draft **did** get a new one generated and emailed
- [ ] Check Render logs for the `trendit` web service around the time of the run — confirm the request hit `/internal/generate-drafts` (if the free instance was spun down, expect a ~30-60s cold-start delay before the request completes)
- [ ] Try running the workflow with a deliberately wrong `INTERNAL_TOKEN` secret (temporarily) → confirm it returns `401` and does **not** run the batch, then restore the correct secret

---

## 9. Regression check — things fixed earlier that could silently break again
- [ ] Re-confirm `requirements.txt` still builds clean (Render deploy log, no `ResolutionImpossible` errors)
- [ ] Re-run the Fernet key check locally: `python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` — confirm it runs without error under the current `cryptography` version (this doesn't test your *actual* stored key, just confirms Fernet itself still works post-bump; full re-verification of the live `CREDENTIALS_ENCRYPTION_KEY` still needs a real decrypt/encrypt round-trip against a stored credential)
- [ ] Confirm `/` homepage still loads normally after a **non**-no-GBP auth failure (e.g. deny consent on Google's screen) — it won't show a nice banner yet (known open item), but confirm it doesn't crash

---

## What "fully working" looks like at the end of this
A brand-new business owner with a real GBP can: sign up → connect → get a confirmation email → complete the wizard → get a first draft emailed within a minute → approve it → see it published live on their Google listing → and, without doing anything else, get a fresh draft emailed to them again the next day (or whenever the cron next runs) — as long as they've acted on the previous one.

If any section above fails, stop and report which numbered item failed rather than continuing — several of today's bugs only became visible because an earlier step silently returned success while doing the wrong thing underneath.
