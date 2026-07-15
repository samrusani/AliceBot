import { describe, expect, it } from "vitest";

import { parseLegacySurfacesFlag } from "./legacy-surfaces.server";

describe("legacy surface server flag", () => {
  it.each([undefined, "", "0", "true", "TRUE", "yes", "on", " 1", "1 ", "2"])(
    "rejects non-exact value %s",
    (value) => {
      expect(parseLegacySurfacesFlag(value)).toBe(false);
    },
  );

  it("accepts only the exact string 1", () => {
    expect(parseLegacySurfacesFlag("1")).toBe(true);
  });
});
