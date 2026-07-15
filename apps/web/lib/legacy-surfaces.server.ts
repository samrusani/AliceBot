/** Resolve the process-wide legacy-surface switch once, when the server module mounts. */
export function parseLegacySurfacesFlag(value: string | undefined): boolean {
  return value === "1";
}

const legacySurfacesEnabledAtMount = parseLegacySurfacesFlag(
  process.env.ALICE_LEGACY_SURFACES,
);

export function legacySurfacesEnabled(): boolean {
  return legacySurfacesEnabledAtMount;
}
