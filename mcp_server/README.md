# mcp_server/ — forked jmdurant/gbp-mcp-server

**Correction from earlier planning:** this is a **Node/TypeScript** project
(built with `npm run build`, run as `node build/index.js`), not Python.
Adjust any assumptions accordingly — including `app/agent/agent.py`'s
`McpToolset`, which now launches it via `node`, not `python`.

## Real project structure (from the actual repo)
```
src/
├── index.ts               # main server entry point
├── server/
│   ├── mcpServer.ts        # core MCP server setup
│   ├── tools/               # tool implementations (incl. Local Posts)
│   ├── resources/
│   └── prompts/
├── services/
│   ├── googleAuth.ts        # <-- THIS is what needs to change
│   ├── reviewService.ts
│   └── llmService.ts
├── types/
└── utils/
```

## Bring in the fork
```bash
git submodule add https://github.com/<your-fork>/gbp-mcp-server.git mcp_server
cd mcp_server
npm install
npm run build
```

## The real problem to fix: `src/services/googleAuth.ts`

The stock auth flow is **interactive and single-user by design**:
```bash
npm run auth   # opens a browser, does OAuth, saves tokens to a local file
```
This works for one personal Google account. It breaks the moment a second
customer connects — there's no `customer_id`/`location_id` concept anywhere
in the flow, and the token file gets overwritten.

### What actually needs to change
1. **In `googleAuth.ts`**, find wherever tokens are read/written (likely a
   local JSON file path, or an in-memory singleton loaded once at startup).
   Replace both the read and write paths with calls out to this backend's
   Postgres-backed store (`app/credentials/store.py`) — since the fork is
   TypeScript and this backend is Python, you have two options:
   - **(A) HTTP call — already built, use this one:** this backend now
     exposes `GET /internal/gbp-credentials?customer_id=...&location_id=...`
     (see `app/internal.py`), authenticated via an `X-Internal-Token` header
     that must match the `INTERNAL_TOKEN` env var (already set in your
     Render env). Have `googleAuth.ts` call this instead of reading a local
     file — pass `BACKEND_URL` (already in your Render env) as the base URL.
   - **(B) Direct Postgres**: have `googleAuth.ts` connect to the same
     Postgres instance directly (via `pg` npm package) and read/write
     `gbp_credentials` itself, matching the encryption scheme in
     `app/credentials/store.py` (Fernet) or switching that table to
     pgcrypto so both languages can decrypt it consistently.

   **(A) is recommended** — keeps all credential logic in one language/place,
   and this backend already owns encryption.

2. **Every tool in `src/server/tools/` that touches the GBP API** currently
   assumes "the one authenticated user." Each of the 4 Local Posts tools
   (`get_local_posts`, `create_local_post`, `update_local_post`,
   `delete_local_post`) needs a `customer_id`/`location_id` (or just
   `location_id`, since Google's location IDs are already unique) threaded
   through its input schema, used to look up the right token via option
   (A) or (B) above instead of the single global token.

3. **Replace the interactive `npm run auth` step entirely** for production
   use — real customers can't run a CLI command. The actual OAuth exchange
   should happen through your **website's existing "connect profile"
   button** (already built per the roadmap), whose callback calls
   `save_credentials()` in `app/credentials/store.py` directly (same
   Python process, no need to go through the Node server at all for the
   *initial* token exchange — only *ongoing* reads/refreshes during tool
   calls need the Node↔Postgres bridge above).

## Leave untouched
Everything in `src/server/tools/`, `src/services/reviewService.ts`,
`src/services/llmService.ts`, and the general MCP protocol plumbing in
`src/server/mcpServer.ts` — only the credential-loading half of the auth
path changes.

## Verifying the swap worked
1. Run the website OAuth flow for two different test customers.
2. Confirm both sets of tokens land in `gbp_credentials` (via
   `app/credentials/store.py`), not a local file.
3. Call `get_local_posts` for each customer's `location_id` through the MCP
   server and confirm each returns *that* customer's posts — the original
   single-file bug (customer B's connect overwriting customer A's tokens)
   is the thing this fork exists to fix.
