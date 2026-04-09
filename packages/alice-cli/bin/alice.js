#!/usr/bin/env node

import { helloAlice } from "@aliceos/alice-core";

const args = process.argv.slice(2);
const version = "0.1.0";

if (args.includes("--version") || args.includes("-v")) {
  console.log(version);
  process.exit(0);
}

if (args.length === 0 || args.includes("--help") || args.includes("-h")) {
  console.log(`alice ${version}

Usage:
  alice hello
  alice --help
  alice --version`);
  process.exit(0);
}

if (args[0] === "hello") {
  console.log(helloAlice());
  process.exit(0);
}

console.error(`Unknown command: ${args[0]}
Run "alice --help" for usage.`);
process.exit(1);
