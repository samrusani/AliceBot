import { describe, expect, it } from "vitest";

import { memoryProvenanceLabel, memoryProvenanceRole } from "./memory-provenance";

describe("memoryProvenanceRole", () => {
  it("reads the role from vNext metadata_json", () => {
    expect(
      memoryProvenanceRole({ metadata_json: { provenance_role: "user" }, value: { text: "I paid $50" } }),
    ).toBe("user");
    expect(memoryProvenanceRole({ metadata_json: { provenance_role: "assistant" } })).toBe("assistant");
  });

  it("falls back to a role carried inside the memory value", () => {
    expect(memoryProvenanceRole({ value: { amount: "$150", provenance_role: "user" } })).toBe("user");
  });

  it("prefers metadata_json over value when both carry a role", () => {
    expect(
      memoryProvenanceRole({
        metadata_json: { provenance_role: "assistant" },
        value: { provenance_role: "user" },
      }),
    ).toBe("assistant");
  });

  it("returns null for unknown, malformed, or missing provenance", () => {
    expect(memoryProvenanceRole({ value: { merchant: "Thorne" } })).toBeNull();
    expect(memoryProvenanceRole({ value: "plain string" })).toBeNull();
    expect(memoryProvenanceRole({ value: ["user"] })).toBeNull();
    expect(memoryProvenanceRole({ metadata_json: { provenance_role: "system" } })).toBeNull();
    expect(memoryProvenanceRole({})).toBeNull();
  });
});

describe("memoryProvenanceLabel", () => {
  it("labels user-derived memories as 'You said'", () => {
    expect(memoryProvenanceLabel({ metadata_json: { provenance_role: "user" } })).toBe("You said");
  });

  it("labels assistant-derived memories as 'Assistant suggested'", () => {
    expect(memoryProvenanceLabel({ metadata_json: { provenance_role: "assistant" } })).toBe(
      "Assistant suggested",
    );
  });

  it("returns null when the role is unknown so cards render unchanged", () => {
    expect(memoryProvenanceLabel({ value: { merchant: "Thorne" } })).toBeNull();
  });
});
