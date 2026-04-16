# Case Study Candidate: `dp-finops-console`

Status snapshot: April 16, 2026

## Partner
- partner key: `dp-finops-console`
- lifecycle stage: `active`
- workspace posture: linked, instrumentation ready
- publication posture: candidate underway

## Starting Point
- initial pain: provider switching added operator uncertainty during production-like reviews
- prior workflow: manual comparison across runtime/provider combinations with inconsistent evidence capture
- reason for selecting Alice: the team needed a continuity surface that could preserve context while changing provider backends

## Pilot Scope
- goal: prove provider switching confidence under production-like finance-operations usage
- review window: rolling 7-day usage summary checked in the weekly launch review
- launch owner: tracked in the hosted-admin support checklist

## Evidence So Far
- notable wins:
  - the first runtime summary window stayed visible after workspace linkage and operator onboarding
  - structured feedback captured a positive signal on provider switching confidence
- notable issues:
  - quote-approval and publication scope are still pending
- structured feedback references:
  - `DPF-2026-04-08-01`
  - `DPF-2026-04-14-01`

## Next Gate
- confirm quote-approval owner
- decide whether the publication form is a short case study or a longer design-partner note
- keep the candidate in `drafting` only after the next review confirms the evidence window remains stable
