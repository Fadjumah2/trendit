# GBP AI Agent SaaS — Project Knowledge (Trendit)
*Last updated: August 8, 2026 — reflects the workflow redefinition session (connect → location selection → suggestions → generation → dual approval → scheduled publish).*

## 1. Product Overview
An AI agent, built on **Google's ADK (Agent Development Kit)**, that manages a small business's **Google Business Profile (GBP)** — starting with automated post drafting (Standard/Event/Offer/Alert), expanding feature-by-feature toward full GBP management.

- **Product name:** Trendit
- **Frontend repo name:** `Fadjumah2/Trenitw` (public on GitHub, deployed on Vercel at `trenitw-kohl.vercel.app`) — note the repo/product name mismatch (Trenitw vs Trendit); cosmetic only, not worth renaming mid-build.
- **Backend repo:** `Fadjumah2/trendit` (public on GitHub, deployed on Render as a Docker Web Service)
- **Target customer:** individual small business owners
- **Scope for v1:** single-location businesses only (multi-location/agency support is a later tier) — note: the *connect flow* must still handle Google accounts that manage multiple locations (see Section 3), even though a given Trendit customer only activates one.
- **v1 feature focus:** posts/content automation. Reviews, Q&A, and insights come later, one at a time.

## 2. Architecture

### Core stack
- **Agent runtime:** Google ADK `LlmAgent` (Gemini) as orchestrator — built and wired
- **GBP access:** ADK `McpToolset` pointed at a forked MCP server (`jmdurant/gbp-mcp-server` fork) — no hand-written API calls
- **Database:** dedicated PostgreSQL instance on Render ("Trendit DB"), Free plan — **Render deletes it August 25, 2026 unless upgraded before then.**
- **Hosting:** single Render Web Service, Docker runtime, manual (not Blueprint)
- **Interaction layer (v1 active): Email + Website**, both routes to the same approval backend logic (see Section 3, Approval)
- **Interaction layer (built, parallel, currently unused): Telegram bot** — paused due to a personal account access issue, not a design flaw
- **OAuth/onboarding:** website "Connect Google Business Profile" button → `/auth/google` → Google consent → `/auth/callback` → backend `/oauth/callback` → location discovery/selection → `/onboarding` wizard → `/dashboard`

### MCP server choice
Fork of `jmdurant/gbp-mcp-server` (Node/TypeScript). Kept 100% of its GBP tool logic; replaced only credential storage — tokens keyed by `customer_id`/`location_id`, stored in Postgres `gbp_credentials`, encrypted via `CREDENTIALS_ENCRYPTION_KEY` (Fernet). v1 exposes the 4 Local Posts tools plus location-listing.

---

## 3. Redefined end-to-end workflow (locked in this session)

This replaces the old "one-time trigger at onboarding completion" model with an explicit, always-visible-status pipeline. Every step below must surface a clear outcome to the user (e.g. "Connected successfully," "Draft generated," "Approved — queued for next publish window," "Published").

### 3a. Connect
1. User clicks Connect → Google consent screen → `/auth/callback` (frontend) → `POST /oauth/callback` (backend).
2. Backend calls the location-listing GBP API for that authenticated account.
3. **Branch on result:**
   - **Zero locations** → existing `HTTPException(422, "no_gbp_found")` → frontend redirects to `/setup-gbp` (unchanged).
   - **Exactly one location** → auto-selected, proceed directly.
   - **Multiple locations** → **new requirement:** show a location picker (name + address per location) before proceeding. Nothing is persisted as "the" managed location until the user picks one.
4. Once a location is resolved: customer + encrypted credentials saved, scoped to that `location_id`.
5. UI shows **"Connected successfully."** Confirmation email fires (`send_connection_confirmation()` — existing, unchanged).

### 3b. Onboarding
6. Wizard collects category/services/tone/target customer/promos → `complete_onboarding_process()` → `business_content_profiles` row saved via Gemini.
7. UI shows **"Profile setup complete."**
8. **Change from previous session:** onboarding completion no longer auto-fires a draft generation call. Generation is now exclusively user-initiated (see 3d) or, when a schedule exists, run by the daily cron. This removes the old "one-time trigger" special case entirely — there is now exactly one generation code path, not two.

### 3c. Suggestions (new capability — replaces the old standalone "Audit" phase)
This is **not a discrete pipeline step** the customer passes through once. It's an always-available agent capability, callable any time from the dashboard, because the agent already has live read access to the profile via the MCP toolset — there's no need to snapshot it once at signup.
- Agent reads current profile state (categories, attributes, hours, description completeness, posting cadence, review recency where available) and surfaces gaps and strengths.
- **Moat feature:** beyond reporting gaps, the agent can *offer to fix them directly* — e.g., propose filling a missing attribute or updating a stale description — by drafting the change and routing it through the **same approval loop as posts** before writing to the live listing (open design assumption, see Section 5).
- Not required for v1 launch; documented here so it's built as "agent capability" rather than re-litigated as a "phase."

### 3d. Draft generation
9. **Single trigger model:** user presses "Generate Draft" on the dashboard. That's it — there is no separate generation-cadence scheduler. (Corrects an earlier version of this plan that proposed one; rejected in favor of simplicity.)
10. `generate_post_draft()` runs → validator runs → `post_history` row saved with `status = 'pending_approval'`.
11. **Email always fires** on generation, regardless of anything else. Dashboard also shows the pending draft with inline Approve/Reject controls (new — previously only the email link existed).

### 3e. Approval
12. User approves or rejects via **either** the website button or the email link. Both must call the same idempotent backend logic — the existing `post_history.owner_decision` double-processing guard already covers this; it just needs a website-side route added alongside the existing email `/approve/{id}` and `/reject/{id}` routes.
13. **Behavior change from previous code:** approving a post does **not** call `publish_post()` immediately. It sets `status = 'approved'` and the post sits in a queue. Publishing is now decoupled from approval timing — see 3f.

### 3f. Scheduled publish
14. **One fixed daily cron, 6:00 AM**, runs every 24 hours (same recurring-trigger mechanism as the existing GitHub Actions setup). It queries all `post_history` rows with `status = 'approved'` and calls `publish_post()` for each, then marks them `published`.
15. There is no per-post custom publish time chosen by the user — every approved post goes out at the next 6:00 AM sweep. Example: approved Tuesday 2pm → publishes Wednesday 6am.
16. **Open edge case (undecided):** a post approved at, say, 5:59am — does it publish in that same imminent 6am run, or wait for the next cycle 24 hours later? Not yet decided; low priority, flag for a later small decision.
17. UI shows **"Published"** once the cron completes for that post; a publish-confirmation email is a reasonable addition here (not yet built).

---

## 4. Current end-to-end flow (updated diagram)

```
/ or /signup (Business Name + Email)
   → GoogleConnectButton → /auth/google → Google consent screen
   → /auth/callback (frontend) → POST /oauth/callback (backend)
       ├─ no GBP found → HTTPException 422 → frontend redirects to /setup-gbp
       ├─ 1 location found → auto-selected
       └─ 2+ locations found → location picker shown → user selects one
   → customer created, credentials saved, confirmation email sent → "Connected successfully"
   → redirect to /onboarding?connected=1&customer_id=...&location_id=...
   → OnboardingWizard (category → services → tone → target customer → promos → review)
   → POST /oauth/onboarding/complete
       → complete_onboarding_process() builds business_content_profiles via Gemini
       → "Profile setup complete" (NOTE: no auto-generation call here anymore)

[Any time after onboarding, repeatable, dashboard-driven:]
   → User taps "Generate Draft"
       → generate_post_draft() → validator → post_history (status=pending_approval)
       → email fires + dashboard shows pending draft
   → User approves (site button OR email link — same backend logic)
       → status → 'approved' → queued, not yet published
   → Daily 6:00 AM cron sweeps all status='approved' rows
       → publish_post() → MCP create_local_post → live on GBP
       → status → 'published'

[Any time, independent of the above, dashboard-driven:]
   → User (or agent proactively) requests Suggestions
       → agent reads live profile state → surfaces gaps/strengths
       → optionally proposes a fix → routed through same approval loop as posts
```

---

## 5. Known open items (not yet fixed, need a decision)

- **Location picker UI + backend support** for accounts managing multiple GBP locations — not yet built.
- **Website-side approve/reject routes** mirroring the existing email routes — not yet built; must share the same idempotency guard.
- **Daily 6:00 AM publish cron** — not yet built. Replaces the old "no recurring trigger" open item entirely; the decision has now been made (single fixed daily sweep, no per-post custom timing).
- **`post_history` needs a clean `approved`-queue query path** — likely just relying on `status = 'approved'`, but confirm no other state needs distinguishing (e.g. approved-but-edited).
- **Suggestions / profile-write capability** — not yet built. Open design question: should agent-proposed profile edits go through the *same* approval loop as posts? Current assumption is yes, for consistency and safety, but this needs explicit confirmation before building.
- **Same-day vs. next-cycle publish edge case** for approvals landing just before the 6am cron — undecided, low priority.
- **`/` homepage doesn't render the generic `auth_failed` error banner** — unchanged from previous session, still open, still low priority.
- **Fernet key re-verification** after the `cryptography>=45,<47` bump — not yet explicitly re-tested against the live `CREDENTIALS_ENCRYPTION_KEY`.
- **Full smoke test still pending** against the *new* workflow — the old `FUNCTIONALITY_TESTS.md` checklist predates this redefinition and needs to be rewritten to match, not just re-run.
- **GBP API quota still at zero** — access-request approval pending with Google. Mock Mode remains the only way to exercise `create_local_post` and location-listing end-to-end until approved. See Section 6.

---

## 6. GBP API quota status (new section)

- OAuth client has the restricted `business.manage` scope already **approved** — this is a completed, valuable asset.
- Separate, independent step: the **access-request / quota approval** for the project is still pending (project shows quota as zero/throttled until Google approves). This is per-GCP-project, not per-account, and is unaffected by OAuth consent screen "Internal vs External" setting or by using a Workspace/enterprise Gmail — those levers do not move quota.
- **Do not switch the OAuth consent screen to "Internal."** Internal restricts sign-in to users within your own Workspace organization, which would lock out all real customers (who authenticate with their own personal/business Google accounts, not yours). Must remain **External**.
- **Interim strategy while waiting:**
  1. Mock at the single interception point inside `mcp_server/` where it would normally call Google's REST API — not via an external mock server, since ADK's `McpToolset` talks to the fork over stdio, not HTTP.
  2. Mock payloads should be validated against Google's actual published JSON schemas for the 4 Local Posts endpoints (`localPosts.create/list/patch/delete`) plus location-listing — not hand-written from memory, to avoid "works in mock, breaks in prod" field-mismatch bugs.
  3. Mock Mode should cover error responses (429 quota-exceeded, 400 invalid field, 401 expired token) in addition to happy-path 200s, so validator and error-handling logic get exercised too.
  4. A refresh token can be pre-staged now via Google OAuth Playground (using the real client ID/secret and `business.manage` scope) and dropped into the `GOOGLE_REFRESH_TOKEN` dev var — this validates consent screen configuration but does **not** bypass quota; calls made with that token still return 429 until the project itself is approved.
  5. Check quota status per-API (not just once) in GCP Console → APIs & Services → each of the 8 Business Profile APIs individually → Quotas & System Limits tab — it's possible some show nonzero before others.

---

## 7. Key learnings (cumulative)

- GitHub's web UI blocks automated tree/search browsing (robots.txt) — zipping and uploading the repo (excluding `node_modules`/`.git`) is the reliable way to get a full, accurate read for debugging.
- A pipeline can look "fully built" in code while being completely unreachable in production because nothing calls the entry point — always trace the actual call graph, not just check that files exist.
- Silent fallbacks are dangerous in a connect/onboarding flow — they let failure cascade through several downstream steps before surfacing.
- When a coding assistant applies a fix, verify the actual diff landed before assuming it's resolved.
- **New this session:** don't build a rigid multi-step "phase" (e.g. audit-as-onboarding-step) when the underlying data is available live at any time — model it as an on-demand agent capability instead. This avoids stale-snapshot bugs and matches how the agent actually has access to the API.
- **New this session:** separate *approval* from *publish timing* early — coupling them (approve = instant publish) works for a v1 demo but doesn't match the "predictable daily posting cadence" behavior small business owners actually want, and is harder to retrofit later than to design correctly now.
