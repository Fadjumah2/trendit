# Bugfix handoff — connect flow + reject button

Three bugs found via full code review of `trendit-main` and `Trenitw-main`
zips. Apply all three, then redeploy and run `FULL_SMOKE_TEST.md`.

---

## 1. `app/routes/oauth.py` — CRITICAL, blocks the entire connect flow

Two stacked bugs in `oauth_callback()`:

**Bug A (line ~101):** `body.businessName` doesn't exist on `CallbackBody`
(the field is `business_name`). This raised `AttributeError` on **every**
single call to `POST /oauth/callback`, before any discovery/mock-mode logic
even ran.

**Bug B (was ~line 177-182):** a block referenced `pool` and `customer_id`
before they were defined later in the function (`pool = get_pool()` and
`customer_id = ...` were both further down). This is an `UnboundLocalError`
in Python — it would fire almost every time since `business_name` is
basically always truthy at that point (mock mode always sets it).

**Fix applied:** changed `body.businessName` → `body.business_name`, and
removed the premature update block. The customer INSERT further down (which
was already correct code, just unreachable) now uses the resolved
`business_name` variable instead of only `body.business_name` — this also
fixes a latent issue where a name discovered via mock mode or real Google
discovery was never actually being saved to the `customers` table.

**Apply:** replace `app/routes/oauth.py` with the attached `oauth.py`.

---

## 2. `app/routes/approval.py` — Reject button does nothing

`reject_post()` checked `owner_decision` but never called `mark_skipped()`
and never returned a response on the success path — it fell through and
implicitly returned `None`, which FastAPI can't turn into the declared
`HTMLResponse`. Clicking Reject in a draft email would fail.

**Fix applied:** added `await mark_skipped(post_id)` and a proper
`HTMLResponse` confirmation, matching the pattern already used by
`approve_post()` and the review-reply reject endpoint just below it.

**Apply:** replace `app/routes/approval.py` with the attached `approval.py`.

---

## 3. Frontend — stray duplicate route file (cosmetic only)

`Trenitw-main/src/routes/src/routes/setup-gbp.tsx` was an orphaned, older,
differently-written duplicate of `src/routes/setup-gbp.tsx`, nested one
level too deep. Confirmed it never made it into `routeTree.gen.ts`, so it
wasn't live — just clutter that risked someone editing the wrong copy.

**Apply:** delete the file and its now-empty parent dirs:
```
rm -rf src/routes/src
```

---

## After applying

1. Redeploy backend to Render, redeploy frontend to Vercel.
2. Run through `FULL_SMOKE_TEST.md` sections 1-7 for real — this is the
   first time the connect flow will actually be able to complete, since
   bug #1 above has been silently blocking it.
3. Watch Render logs during the first live OAuth callback — the `DEBUG:`
   print statements already in `oauth.py` will show whether mock mode or
   real discovery is engaging, and what `location_id`/`business_name` got
   resolved.
