import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const semver = require("semver");

const ADVISORY_SEVERITIES = new Set([
  "info",
  "low",
  "moderate",
  "high",
  "critical",
]);

function isPlainObject(value) {
  if (value === null || typeof value !== "object" || Array.isArray(value)) {
    return false;
  }
  const prototype = Object.getPrototypeOf(value);
  return prototype === Object.prototype || prototype === null;
}

/**
 * Validate the npm bulk advisory response before an empty result can pass CI.
 *
 * The endpoint contract is package name -> advisory[]. A successful HTTP/JSON
 * exchange is not sufficient evidence that this contract was honored: arrays,
 * null, and partially malformed advisory objects must fail the audit closed.
 */
export function validateBulkAdvisoryResponse(payload) {
  if (!isPlainObject(payload)) {
    throw new TypeError("bulk advisory response must be a plain object");
  }

  for (const [packageName, advisories] of Object.entries(payload)) {
    if (!Array.isArray(advisories)) {
      throw new TypeError(
        `bulk advisory response for ${JSON.stringify(packageName)} must be an array`,
      );
    }

    advisories.forEach((advisory, index) => {
      const label = `advisory ${JSON.stringify(packageName)}[${index}]`;
      if (!isPlainObject(advisory)) {
        throw new TypeError(`${label} must be a plain object`);
      }

      const range = advisory.vulnerable_versions;
      if (
        typeof range !== "string" ||
        range.trim() === "" ||
        semver.validRange(range) === null
      ) {
        throw new TypeError(`${label} has an invalid vulnerable_versions range`);
      }

      const severity = advisory.severity;
      if (
        typeof severity !== "string" ||
        !ADVISORY_SEVERITIES.has(severity.toLowerCase())
      ) {
        throw new TypeError(`${label} has an invalid severity`);
      }

      for (const field of ["title", "url"]) {
        if (field in advisory && typeof advisory[field] !== "string") {
          throw new TypeError(`${label} has a non-string ${field}`);
        }
      }
    });
  }

  return payload;
}
