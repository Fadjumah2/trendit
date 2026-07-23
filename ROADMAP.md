# Trendit — Agent Roadmap & Guardrails

**Read this before touching any code.** This file exists because different
coding agents (or the same agent in different sessions) will otherwise
re-derive architecture decisions from scratch, sometimes differently each
time. Treat the "Non-negotiable rules" section as constraints, not
suggestions — deviating from them reintroduces bugs this project already
fixed once.

---

## 1. What Trendit is

An AI agent (built on Google's ADK, orchestrating Gemini) that manages a
small business's Google Business Profile — starting with automated post
drafting (Standard/Event/Offer/Alert), expanding feature-by-feature later.
v1 scope: single-location businesses, posts only. Interaction happens via
Telegram. Full product context lives in `gbp-ai-agent-plan.md` in this
project — read that for the "why," this file is the "how, precisely."

---

## 2. Non-negotiable rules

These exist because a specific real bug already happened once (the stock
MCP server's single shared token file) and a second near-miss almost
happened during this build (a proposed per-instance `GoogleAuthService`
pattern that would have reintroduced cross-customer leakage if any caller
ever pooled or reused instances). Any agent working on this repo must
follow these:

1. **No credential state cached on shared objects.** Every function that
   needs a customer's GBP tokens takes `location_id` (Google's location
   IDs are globally unique — no need for `customer_id` alongside it in
   most lookups) as a plain argument and fetches fresh from Postgres each
   call. Do not introduce constructors that load-and-cache tokens, even
   "per customer" ones, unless you can guarantee — structurally, not by
   convention — that instances are never pooled or reused across requests.
   When in doubt, prefer the stateless function-per-call pattern already
   in `mcp_server_patches/`.

2. **Postgres (`gbp_credentials`) is the single source of truth for
   tokens.** Never let the Node MCP server write tokens to a local file,
   env var, or in-memory cache that outlives one request. Reads/writes go
   through the Python backend's `/internal/gbp-credentials` endpoints
   (`app/internal.py`), authenticated by `INTERNAL_TOKEN`.

3. **Initial OAuth token issuance happens on the website, not the MCP
   server.** The website's existing "connect profile" button drives the
   OAuth consent flow; its callback exchanges the auth code and calls
   `save_credentials()` in `app/credentials/store.py` directly (same
   Python process). The Node MCP server's `getAuthUrl`/`handleCallback`
   exist only for local dev/testing against the developer's own account —
   never wire them into a customer-facing flow.

4. **`GOOGLE_CLIENT_ID`/`GOOGLE_CLIENT_SECRET` are shared across all
   customers** (they identify the app to Google). **`GOOGLE_REFRESH_TOKEN`
   is a single dev-only value** (the developer's own OAuth Playground
   token) and must never be read on any code path that serves a real
   customer request. Production always resolves tokens per-location from
   Postgres.

5. **The deterministic validator (`app/validator/validator.py`) is not
   optional and not replaceable by another LLM call.** Every LLM-drafted
   post must pass through it before reaching the MCP `create_local_post`/
   `update_local_post` tools. Char limits, CTA enum, required fields, and
   PII/URL regex checks stay code-level, not prompt-level.

6. **The MCP tool surface exposed to the agent stays filtered.** v1 only
   sees the 4 Local Posts tools (`get_local_posts`, `create_local_post`,
   `update_local_post`, `delete_local_post`) via `tool_filter` in
   `app/agent/agent.py`. Do not widen this list until a phase explicitly
   calls for it (see roadmap below) — the point is limiting blast radius
   while reviews/Q&A/insights aren't built or tested yet.

7. **The agent never touches Telegram formatting.** It only ever produces
   post *content* (title/body/cta/etc. as structured data). All
   `parse_mode`, inline keyboards, and message templates live in
   `app/telegram/templates.py` and `app/telegram/client.py`.

8. **Don't split the repo further.** ADK agent, forked MCP server (as
   `mcp_server/`), Telegram webhook, and validator all live in one
   `backend` repo. Database has no repo of its own — migrations live under
   `backend/migrations/`. The website is a separate repo on Vercel; that
   boundary is intentional and stays as-is.

9. **Never commit `.env`.** Real secrets live in Render's env vars (and a
   local `.env` for dev, gitignored). `.env.example` is the only version
   that gets committed, with empty/placeholder values.

10. **Naming: the product is called Trendit.** Older docs/comments may
    still say "Signups" or generic names — update them opportunistically
    when touched, but this isn't worth a dedicated pass on its own.

---

## 3. Current state (update this section as work lands)

| Piece | Status |
|---|---|
| Postgres schema (`customers`, `gbp_credentials`, `telegram_chat_links`, `telegram_link_codes`, `business_content_profiles`, `post_history`) | ✅ Built (`migrations/001_init_schema.sql`, `002_telegram_link_codes.sql`) |
| Credential storage (Python side) | ✅ Built (`app/credentials/store.py`) — per-customer and per-location lookups both exist |
| Internal credentials bridge (Node → Python) | ✅ Built (`app/internal.py`) — GET by location, POST refresh pushback |
| Policy rules config + deterministic validator | ✅ Built (`app/agent/policy_rules.json`, `app/validator/validator.py`) |
| Content profile service | ✅ Built (`app/agent/content_profile.py`) — read/write only; nothing populates it yet (Phase 2) |
| ADK agent + McpToolset wiring | ⚠️ Scaffolded (`app/agent/agent.py`) — needs verification against current `google-adk` docs; not yet tested against a live MCP server |
| Telegram webhook, templates, linking flow | ✅ Built (`app/telegram/`) — not yet tested end-to-end against a real bot |
| post_history service + publish step | ⚠️ `services/post_history.py` built; `services/publish.py` is a **stub** — the actual MCP `create_local_post` call isn't wired in yet |
| Forked MCP server (`mcp_server/`) | 🚧 In progress — `googleAuth.ts`/`tokenStorage.ts` patches drafted in `mcp_server_patches/`, not yet confirmed against the real files or applied. Tool files in `src/server/tools/` not yet updated to accept `location_id`. |
| Website OAuth callback → `gbp_credentials` | ❓ Not yet confirmed working end-to-end from this side |
| Onboarding intake form / niche template library | ❌ Not started (Phase 2) |
| Stripe billing | ❌ Not started (Phase 6) |

---

## 4. Phased roadmap

### Phase 1 — Backend Core (in progress)
- [x] Postgres schema
- [x] Credential storage (Python side, both directions)
- [ ] Apply `mcp_server_patches/` to the real fork; confirm field names against actual `tokenStorage.ts`/`config.js`
- [ ] Update every tool in `src/server/tools/` to accept and use `location_id`
- [ ] Verify website OAuth callback writes correctly into `gbp_credentials`
- [ ] End-to-end test: two different test locations, confirm no token cross-contamination

### Phase 2 — Content Intelligence
- [ ] Onboarding intake form (category, services, tone, target customer, promos)
- [ ] Niche prompt-template library
- [ ] One-time signup LLM call → `business_content_profile` JSON → Postgres
- [ ] Feedback logging (owner edits/rejections) to refine the profile

### Phase 3 — ADK Agent
- [ ] Confirm `McpToolset`/`StdioServerParameters` usage against current ADK docs (flagged uncertain in `agent.py`)
- [ ] Wire `services/publish.py`'s stub to the real `create_local_post` call once Phase 1's tool signatures are final
- [ ] End-to-end: LLM draft → validator → (await approval) with a real MCP connection, mock GBP data is fine at this stage

### Phase 4 — Telegram Interaction Layer
- [ ] Register real webhook, confirm secret-token check works
- [ ] Test linking flow with a real chat_id end-to-end
- [ ] Test approve/edit/skip buttons against a real pending draft

### Phase 5 — Pilot
- [ ] Onboard a handful of real single-location businesses
- [ ] Monitor validator rejections and owner edit patterns
- [ ] Refine content profiles/templates from real feedback

### Phase 6 — Monetization & Growth
- [ ] Stripe billing integration
- [ ] Free/paid tier gating
- [ ] Marketing push

### Phase 7 — Feature Expansion (one at a time, widen `tool_filter` only when ready)
- [ ] Reviews tools → AI-assisted review replies
- [ ] Q&A tools
- [ ] Insights/analytics tools
- [ ] Multi-location support
- [ ] Reconsider ADK MemoryService (Vertex AI RAG) only if fuzzy cross-post recall becomes a real need

---

## 5. Key files, what they're for

```
backend/
├── migrations/                     # SQL, run manually against Render Postgres
├── mcp_server/                     # forked jmdurant/gbp-mcp-server (Node/TS) — see its own README
├── mcp_server_patches/             # drafted replacement files, staged before applying to mcp_server/
├── app/
│   ├── config.py                   # all env vars, real Render names — read this before assuming a var name
│   ├── db.py                       # asyncpg pool
│   ├── main.py                     # FastAPI entrypoint
│   ├── internal.py                 # Node↔Python credential bridge, INTERNAL_TOKEN-gated
│   ├── credentials/store.py        # Postgres-backed OAuth token storage, encrypted at rest (Fernet)
│   ├── agent/agent.py              # ADK LlmAgent + McpToolset, tool_filter = 4 Local Posts tools only
│   ├── agent/content_profile.py    # business_content_profile read/write, few-shot post retrieval
│   ├── agent/policy_rules.json     # distilled GBP post policy, sliced per post type
│   ├── validator/validator.py      # deterministic checks — the safety net before publish
│   ├── telegram/                   # client, templates, linking, webhook — all Telegram specifics live here
│   └── services/
│       ├── post_history.py         # draft/approve/edit/skip state machine
│       └── publish.py              # STUB — final MCP create_local_post call, not yet wired
```

---

## 6. Env vars (real names, already set in Render unless noted)

`AGENT_MODEL`, `DATABASE_URL`, `GOOGLE_API_KEY`, `GOOGLE_CLIENT_ID`,
`GOOGLE_CLIENT_SECRET`, `GOOGLE_REFRESH_TOKEN` (dev-only, see rule #4),
`INTERNAL_TOKEN`, `BACKEND_URL`, `TELEGRAM_TOKEN`, `WEBHOOK_SECRET`,
`PYTHONDONTWRITEBYTECODE`, `PYTHONPATH`.

**Not yet in Render, needs adding:** `CREDENTIALS_ENCRYPTION_KEY` (Fernet
key — generate with the command in `.env.example`).

---

## 7. When an agent proposes a design that conflicts with this file

Stop and flag the conflict explicitly rather than silently picking one —
either the pattern in this file, or something new the agent is proposing,
should win on purpose, not by whichever was implemented most recently. If
you're an AI agent reading this: prefer the stateless, function-per-call
pattern in `mcp_server_patches/` over any singleton/instance-caching
alternative unless a human explicitly overrides rule #1 above.
