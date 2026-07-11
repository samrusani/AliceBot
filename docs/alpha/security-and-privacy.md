# Public Alpha Security And Privacy

Alice public preview is local-first.

Security posture:

- source evidence is review-only
- generated artifacts are review-only
- agent memory proposals are review-only; explicit agent commits may become durable only when the configured policy permits it
- trusted memory is not auto-promoted
- connector secrets should be stored as secret refs
- CLI/API/UI/event/source/artifact output should not print secret values
- prompt-injection source text is data, not policy
- agents are policy-checked by authenticated identity, permission profile, persisted target, project, domain, sensitivity, and action
- a project-bound key inherits its project filter when a read omits one and cannot read or mutate a different project
- all `/v0/vnext` HTTP routes share one authentication boundary: keyless local compatibility ends when the user creates an active key, after which strict Bearer authentication is required
- every route is classified as either target/policy-authorized or central operator-only; once keys exist, central console reads and writes require an unbound `trusted_local_agent` or `admin_agent` key, and unclassified routes fail closed
- artifact get, feedback, quality-rating, review, export, and trace operations authorize the persisted artifact project/domain/sensitivity before returning content or applying a side effect; trace sources are filtered by the same exact-target policy
- the local `/vnext` console accepts an unbound `trusted_local_agent` or `admin_agent` key only through its password field, keeps it only in browser memory for the mounted session, and forwards it only to loopback `/v0/vnext` routes; it never reads the key from environment variables, local storage, URLs, logs, or errors
- `trusted_local_agent` does not grant human/admin review decisions such as artifact acceptance; use a dedicated unbound `admin_agent` key when those actions are needed and revoke it when no longer needed
- the browser-clipper bookmarklet never embeds or prompts for an agent key because visited-page JavaScript is not a trusted credential context; it is a zero-active-key compatibility path only, and keyed deployments must use a trusted API client with Bearer authentication plus `capture_token`
- MCP servers bound with `ALICE_AGENT_API_KEY` expose only the core surface; legacy handlers fail closed because they do not all implement the same persisted-target authorization contract
- the managed SQLite directory is owner-only; database sidecars and exports are also owner-only

Recommended alpha defaults:

```bash
alicebot vnext doctor --fix-safe --ci
alicebot vnext smoke secret-redaction
alicebot eval run --suite all
```

Sensitive domain guidance:

- project-scoped agents should avoid personal, family, health, spiritual, legal, financial, and regulated domains
- trusted local assistants should request sensitive domains only when necessary
- blocked or filtered policy decisions should be surfaced in `/vnext` Agent Activity

Reporting issues:

- include command output with secrets redacted
- include failing smoke names
- do not include private exports, real Telegram payloads, API tokens, or personal datasets
