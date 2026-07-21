# First-run Checklist

Use this checklist after a fresh clone.

| Step | Command or doc | Expected success |
| --- | --- | --- |
| 1. Install Alice | `make setup` | `.venv` and web dependencies exist |
| 2. Run migrations | `make migrate` | Postgres is up and Alembic reaches head |
| 3. Run doctor | `make doctor` | no blocking failures |
| 4. Start API | `APP_RELOAD=false ./scripts/api_dev.sh` | API serves locally |
| 5. Start scheduler | `alicebot vnext scheduler daemon start --foreground` | daemon reports status and due scans |
| 6. Check live browser env | `cat apps/web/.env.local` | `NEXT_PUBLIC_ALICEBOT_API_BASE_URL=http://127.0.0.1:8000` and a local user id are present |
| 7. Start `/vnext` | `pnpm --dir apps/web build` then `pnpm --dir apps/web start --hostname 127.0.0.1 --port 3000` | web app serves locally |
| 8. Open `/vnext` | `http://localhost:3000/vnext` | live mode loads or shows a clear empty state |
| 8a. Authenticate `/vnext` after any key is active | create an unbound `admin_agent` key with `alicebot agent keys create --agent-id vnext-operator --profile admin_agent --label "Local review console"`, then enter the one-time value in **Unbound admin_agent API key** | the full console reloads with session-only Bearer authentication; `trusted_local_agent` is not full admin-review parity |
| 9. Configure Brain Charter | [../vnext/ALICE.example.md](../vnext/ALICE.example.md) | Brain Charter is visible in Settings |
| 10. Configure one capture path | local folder or browser clipper | connector health becomes configured |
| 11. Capture first source | `alicebot vnext sources capture-text "Fact: first alpha source" --domain project --sensitivity private` | source appears in Inbox |
| 12. Review captured source | `/vnext` Inbox | review event appears in Timeline |
| 13. Generate artifact | `alicebot daily-brief --generate --domain project` | artifact appears in Generated |
| 14. Review or rate artifact | `/vnext` Generated | rating appears in dogfooding telemetry |
| 15. Inspect trace | `/vnext` Trace | source, chunks, memories, artifacts, and events link together |
| 16. Connect an agent | [agent-integration.md](agent-integration.md) | context pack, output ingestion, proposal flow, and explicit memory commit gates work |
| 17. Check agentic memory commit | `alicebot vnext smoke agentic-memory-commit` | trusted commit, confirmation, review, undo, correction, forget, and audit gates pass |
| 18. Prove first memory behavior | [first-memory.md](first-memory.md) | tester understands explicit commit, reviewable proposal, and structured capture paths |

When doctor fails, go to [doctor.md](doctor.md) first. It lists the exact command that usually fixes the blocking issue.

For local live mode, `.env` must include `CORS_ALLOWED_ORIGINS=http://127.0.0.1:3000,http://localhost:3000`, and `apps/web/.env.local` must include `NEXT_PUBLIC_ALICEBOT_API_BASE_URL=http://127.0.0.1:8000`.

Keyless local compatibility ends when the first active agent key is provisioned. The console key is
entered per mounted browser session and is never configured through `.env`, local storage, or the
URL. The trusted console can use that session key to issue an origin-bound, short-lived, one-time
browser-clip capability. Prepare a fresh bookmarklet for every clip; the bookmarklet receives
neither the reusable agent key nor a configured `capture_token`.

Use `pnpm --dir apps/web dev` only while editing the web UI. For long-running agent or Hermes sessions, prefer `make runtime` as the combined API plus web command, or use the `next start` command above when API is already running.
