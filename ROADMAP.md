I SHALL USE RENDER FOR HOSTING

GBP AI Agent SaaS — Roadmap (Trendit)
*Updated August 8, 2026 — workflow redefinition: location selection, dropped rigid "audit" phase in favor of an always-on Suggestions capability, and the approve-then-scheduled-publish model (single daily 6am cron, decoupled from approval timing).*

Phase 0 — Foundations (already in place)
[x] PostgreSQL database on Render — dedicated instance ("Trendit DB"). Currently Free plan — Render deletes it August 25, 2026 unless upgraded before then.
[x] Website/frontend with GBP "connect profile" OAuth button
[x] Google GBP API access approved (OAuth scope `business.manage`) — NOTE: this is the *scope* approval only. The separate *quota* access-request is still pending with Google as of this update; project is throttled to zero until that clears. See "GBP API quota" note under Infrastructure notes below.
[x] Telegram bot created via BotFather (token in hand) — built and working, currently not the active channel (see Phase 4b)
[x] Resend account set up, domain forms.trendexhub.com verified, API key in hand

Phase 1 — Connect Flow (Backend Core)
[x] Fork jmdurant/gbp-mcp-server
[x] Design Postgres schema: gbp_credentials, telegram_chat_links, business_content_profiles, post_history, customers, telegram_link_codes
[x] Replace the fork's file-based OAuth token storage with per-customer Postgres-backed storage (encrypted at rest)
[x] Thread location_id through create_local_post/update_local_post/delete_local_post tools
[x] /oauth/callback exists, creates customers, saves credentials, sends confirmation email
[x] No-GBP handling: backend 422 (`no_gbp_found`) + frontend `/setup-gbp` page
[ ] **New: location-listing call after OAuth callback** — fetch all GBP locations the connected account manages
[ ] **New: location picker UI** — if 2+ locations found, show name+address picker before proceeding to onboarding; if exactly 1, auto-select and skip the picker
[ ] Verify token refresh flow works end-to-end against Postgres

Phase 2 — Onboarding / Content Intelligence
[x] Build onboarding intake wizard (category, services, tone, target customer, promos) — frontend (`OnboardingWizard.tsx` etc.)
[x] Implement one-time signup LLM call that compresses intake into a business_content_profile JSON, stored in Postgres (`complete_onboarding_process()`)
[ ] Build niche prompt-template library (per broad business category, with seasonal/event hooks)
[ ] Build feedback logging (owner edits/rejections) to refine the profile over time
[ ] **Change:** onboarding completion no longer auto-triggers a draft generation call (previously did, as a one-time special case). Generation is now exclusively user-initiated via dashboard button — see Phase 3.

Phase 3 — Agent Capabilities
*(Replaces the old "Phase 3 — ADK Agent" pipeline-building phase. The generation pipeline itself — LlmAgent, McpToolset, validator — is already fully built and wired; this phase now tracks agent-facing capabilities layered on top of that pipeline, not the pipeline's existence.)*
[x] ADK LlmAgent (Gemini) with system prompt containing distilled, post-type-sliced GBP policy rules
[x] McpToolset wired to the forked MCP server, filtered to the 4 Local Posts tools for v1 (+ location-listing)
[x] Deterministic code-level validator (char limits, CTA enum, required fields by post type, PII/URL regex, image checks)
[x] Pipeline wired: LLM draft → validator → save (post_history, status=pending_approval) → notify.send_draft_for_approval()
[ ] **New: "Generate Draft" button on dashboard** — the single user-facing trigger for generation (no scheduler triggers generation; see Phase 4c for what the scheduler does instead)
[ ] **New: Suggestions capability** — on-demand (not a fixed onboarding step), agent reads live profile state via MCP toolset and surfaces strengths/gaps (missing attributes, stale description, posting cadence, etc.)
[ ] **New: Suggestion-driven fixes** — agent can propose a specific profile edit (not just report the gap), routed through the same approval loop as posts before writing to the live listing. Open design question: confirm this approval-loop-for-writes assumption before building.

Phase 4a — Email Interaction Layer [x] Built
[x] app/email/client.py — sends via Resend API
[x] app/email/templates.py — draft preview email (Approve/Reject links, HTML-escaped) + confirmation page
[x] app/services/notify.py — send_draft_for_approval(post_id), looks up customer.email, sends
[x] app/routes/approval.py — GET /approve/{post_id} and GET /reject/{post_id}, guarded against double-processing via post_history.owner_decision
[ ] **Change: approval no longer calls publish_post() directly.** Approve now sets status='approved' and queues the post; actual publish happens via the Phase 4c scheduler.
[ ] Confirm a full manual test against the real Render deploy under the *new* approve→queue→scheduled-publish flow (previous manual test validated the old approve→instant-publish flow, now outdated)

Phase 4b — Telegram Interaction Layer (built, parallel, not currently active)
[x] Register Telegram webhook (/telegram/webhook route)
[x] Build chat_id ↔ customer_id linking flow (one-time code from website → sent to bot)
[x] Build message templates (draft preview, published confirmation, error states) + inline keyboard buttons (Approve/Edit/Skip)
[ ] Wire full loop: webhook → load customer context → agent draft → validator → send to owner → button/reply → same approve→queue→scheduled-publish flow as email/website
DO NOT remove or treat Telegram code as dead/deprecated. It's a working parallel frontend, switched away from temporarily due to a personal Telegram/Gmail access issue, not a design flaw. Re-activating it later is a live option per-customer.

Phase 4c — Website Approval + Scheduled Publish (new phase, not in original roadmap)
[ ] **Website-side approve/reject routes** — mirror the existing email `/approve/{id}` and `/reject/{id}` logic so approval/rejection can happen from the dashboard, sharing the same idempotency guard (post_history.owner_decision) as the email routes
[ ] **Dashboard: show pending draft inline** with Approve/Reject controls (currently only reachable via the email link)
[ ] **Daily 6:00 AM publish cron** — single fixed recurring trigger (same mechanism as the existing GitHub Actions daily draft trigger, repurposed) that queries all post_history rows with status='approved' and calls publish_post() for each, then marks published
[ ] **Dashboard: visible per-post status/timeline** — pending_approval → approved (queued) → published, so the user always knows where a given draft stands
[ ] Decide: same-day vs. next-cycle publish for a post approved just before the 6am cron fires (edge case, low priority)
[ ] Publish-confirmation email/notification once the cron completes for a post (nice-to-have, not yet built)

Phase 5 — Pilot
[ ] Onboard a handful of real single-location small businesses
[ ] Monitor validator rejections and owner edit patterns
[ ] Refine content profiles and templates based on real feedback

Phase 6 — Monetization & Growth
[ ] Stripe billing integration
[ ] Free/paid tier gating (post limits, auto-scheduling, analytics)
[ ] Launch marketing: SEO content, local SEO agency referrals, small-business community groups

Phase 7 — Feature Expansion (one at a time)
[ ] Widen McpToolset to add Reviews tools → AI-assisted review replies
[ ] Add Q&A tools
[ ] Add Insights/analytics tools → reporting features
[ ] Multi-location support → agency/franchise tier (note: distinct from the Phase 1 location *picker*, which handles a single customer's Google account managing multiple locations — this phase is about one Trendit customer actively managing several locations at once)
[ ] Consider ADK MemoryService (Vertex AI RAG) if fuzzy cross-post recall becomes necessary

Infrastructure notes
- Backend repo — one repo containing the ADK agent, the forked MCP server (as a subfolder, at mcp_server/), the Telegram webhook handler, the email approval routes, and the validator. Repo root layout: app/, migrations/, mcp_server/, Dockerfile, render.yaml, requirements.txt, ROADMAP.md, README.md — no stray src/ or nested trendit/ subfolder.
- Database — no repo of its own, just migrations living inside the backend repo under /migrations.
- Hosting — deployed as a single Render Web Service (Docker runtime), NOT via Render Blueprint. render.yaml still exists in the repo but is currently unused.
- Dockerfile installs both Python (FastAPI + ADK agent) and Node 20 (for mcp_server/, a TypeScript project) in one image — required because ADK's McpToolset talks to the forked server over stdio, which only works between processes on the same machine/container.
- CREDENTIALS_ENCRYPTION_KEY must be a real Fernet key: python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())" — exactly 44 base64 characters ending in "=". An arbitrary hex/random string will fail at startup with "Fernet key must be 32 url-safe base64-encoded bytes." Still pending re-verification after the cryptography>=45,<47 bump.
- GOOGLE_REFRESH_TOKEN is dev-only — for manually testing MCP tools against a personal GBP listing. Must never be read on the real customer-facing publish path; only gbp_credentials (per customer_id/location_id) is used there. Can be pre-staged now via OAuth Playground even while quota is pending (validates consent screen config; does not bypass quota).
- **GBP API quota** — OAuth scope (`business.manage`) is approved; the separate project-level quota access-request is still pending. Quota is per-GCP-project and is unaffected by OAuth consent screen "Internal vs External" or by Workspace/enterprise Gmail — do not switch consent screen to Internal, it would lock out all real customers. Mock Mode (fake "Trendit Bistro" location) remains the primary development/testing path until quota clears; mock payloads should be validated against Google's real published schemas, and should cover error responses (429/400/401), not just happy-path 200s.

North star (updated) — before any further polish/features: prove the single end-to-end loop once, under the *new* workflow — connect (with location selection) → onboarding → AI drafts a Standard post (user-triggered) → validator checks it → owner approves (site or email) → post sits queued → daily 6am cron publishes it → real create_local_post call → post appears on a real/test GBP listing. Phases 2, 5, 6, 7 remain secondary until this loop is proven. Suggestions (Phase 3, new capability) and Phase 4c's dashboard status timeline are valuable but not required to prove the north star loop.
