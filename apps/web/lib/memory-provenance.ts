/**
 * Speaker-provenance labels for memory cards.
 *
 * Capture stamps `provenance_role` ("user" | "assistant") when a memory was
 * derived from a speaker-tagged conversational turn: vNext memories carry it
 * in `metadata_json`, continuity memories may carry it inside `value`. Cards
 * show a small chip ("You said" vs "Assistant suggested") only when the role
 * is known; memories without provenance render exactly as before.
 */

export type MemoryProvenanceRole = "user" | "assistant";

type ProvenanceCarrier = {
  value?: unknown;
  metadata_json?: unknown;
};

function roleFromRecord(record: unknown): MemoryProvenanceRole | null {
  if (!record || typeof record !== "object" || Array.isArray(record)) {
    return null;
  }

  const role = (record as Record<string, unknown>).provenance_role;
  if (role === "user" || role === "assistant") {
    return role;
  }

  return null;
}

export function memoryProvenanceRole(memory: ProvenanceCarrier): MemoryProvenanceRole | null {
  return roleFromRecord(memory.metadata_json) ?? roleFromRecord(memory.value);
}

export function memoryProvenanceLabel(memory: ProvenanceCarrier): string | null {
  const role = memoryProvenanceRole(memory);
  if (role === "user") {
    return "You said";
  }
  if (role === "assistant") {
    return "Assistant suggested";
  }

  return null;
}
