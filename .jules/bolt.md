# Bolt's Performance Journal ⚡

## 2026-07-26 - [Post history query optimization via composite indexes]
**Learning:** Found that `post_history` is queried frequently filtering on multiple columns (`customer_id`, `location_id`, `owner_decision`) and ordering by `created_at DESC`. Without composite indexes, Postgres is forced to run bitmap index scans combining single-column indexes, filtering rows sequentially, and performing a memory-intensive sort.
**Action:** Created composite indexes (`idx_post_history_query_opt` and `idx_post_history_pending_opt`) to ensure index-only scans and O(log N) sorted retrievals.

## 2026-07-26 - [Robust, zero-latency template fallback on MCP Sampling failures]
**Learning:** In the TypeScript MCP server, `llmService.generateReply()` assumed a flawless execution of `requestSampling` via `extra.sendRequest`. In mock test mode or when the LLM service fails, this caused fatal unhandled exceptions.
**Action:** Encapsulated MCP sampling calls in a try-catch to immediately and gracefully fallback to lightweight local templates, eliminating extra latency on failure paths.
