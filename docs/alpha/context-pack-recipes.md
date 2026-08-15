# Context-pack Recipes

Every recipe uses scoped context and avoids raw unrestricted memory access.

These are `alice_context_pack` arguments. The scope fields are flat properties on the request,
not nested under `scope` and `options`; an unrecognised property is rejected outright rather
than ignored.

## 1. Project Sprint Context

- Purpose: prepare a coding agent for sprint work.
- Agent type: `coding_agent`
- Permission: `project_scoped_agent`

```json
{"query":"current sprint decisions blockers architecture constraints","domains":["project"],"projects":["Alice"],"sensitivity_allowed":["public","internal","private","unknown"],"max_items":10}
```

Next: build or review only within project scope. Do not request personal domains.

## 2. Code Review Context

```json
{"query":"recent changes review findings unresolved risks","domains":["project"],"projects":["Alice"],"sensitivity_allowed":["public","internal","private","unknown"],"max_items":8}
```

Next: cite findings and create open loops for unresolved issues. Do not promote review claims as trusted memory.

## 3. Research Context

```json
{"query":"research notes decisions sources open questions","domains":["project","professional"],"sensitivity_allowed":["public","internal","private","unknown"],"max_items":8}
```

Next: ingest report output. Do not include speculative claims as memory.

## 4. Daily Assistant Context

```json
{"query":"today priorities open loops recent decisions","domains":["personal","professional","project"],"sensitivity_allowed":["public","internal","private","unknown"],"max_items":12}
```

Next: propose only stable preferences or durable decisions.

## 5. Meeting Preparation Context

```json
{"query":"meeting preparation stakeholders decisions open loops","domains":["professional","project"],"sensitivity_allowed":["public","internal","private","unknown"],"max_items":10}
```

Next: generate a reviewable prep artifact. Do not request restricted domains unless needed.

## 6. Investor Or Stakeholder Briefing Context

```json
{"query":"stakeholder briefing milestones risks decisions","domains":["professional","project"],"sensitivity_allowed":["public","internal","private"],"max_items":10}
```

Next: produce a brief with source references. Do not include private personal data.

## 7. Recent Decisions Context

```json
{"query":"recent decisions","domains":["project"],"sensitivity_allowed":["public","internal","private","unknown"],"max_items":10}
```

Next: use decisions as constraints. Do not infer new decisions.

## 8. Recent Changes Context

```json
{"query":"recent changes since last sprint","domains":["project"],"sensitivity_allowed":["public","internal","private","unknown"],"max_items":10}
```

Next: summarize changes and submit output back to Alice.

## 9. Open Loops Context

```json
{"query":"open loops blockers waiting for follow ups","domains":["project","professional"],"sensitivity_allowed":["public","internal","private","unknown"],"max_items":10}
```

Next: close only through review paths. Do not silently delete loops.

## 10. Contradiction Check

```json
{"query":"possible contradiction around current project direction","domains":["project"],"sensitivity_allowed":["public","internal","private","unknown"],"include_contradictions":true,"max_items":8}
```

Next: surface contradictions for review. Do not resolve without user confirmation.

## 11. Long-running Task Resumption Context

```json
{"query":"resume long running task current state decisions blockers","domains":["project"],"projects":["Alice"],"sensitivity_allowed":["public","internal","private","unknown"],"max_items":12}
```

Next: continue from cited context and create an output summary at the end.
