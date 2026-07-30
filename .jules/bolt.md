# Bolt's Performance Journal

## 2026-07-25 - Missing unique lookup index and APIs in a hybrid multi-tenant architecture
**Learning:** In a hybrid architecture where a Node.js process delegates credential storage and operations to a Python FastAPI backend via an internal API, failing to index the lookup key (`location_id`) on the database forces costly sequential scans on every single tool call. Additionally, omitting standard operations like POST (refresh) and DELETE (disconnect) on the backend completely stalls token lifecycle management.
**Action:** Always verify that all cross-service query keys are fully indexed (e.g., using `CREATE UNIQUE INDEX` for unique third-party resource IDs), and ensure all CRUD lifecycle methods required by client services are fully implemented on backend microservices.
