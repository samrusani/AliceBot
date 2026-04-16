#!/usr/bin/env node

import { spawn } from "node:child_process";

const args = process.argv.slice(2);
const version = "0.5.1";
const defaultPythonCommand = process.platform === "win32" ? "python" : "python3";

function forwardToPython(moduleName, moduleArgs, errorLabel) {
  const pythonCommand = process.env.ALICEBOT_PYTHON || defaultPythonCommand;
  const child = spawn(
    pythonCommand,
    ["-m", moduleName, ...moduleArgs],
    {
      stdio: "inherit",
      env: process.env,
    },
  );

  child.on("error", (error) => {
    console.error(
      `Failed to start ${errorLabel} using "${pythonCommand}": ${error.message}
Set ALICEBOT_PYTHON to your Alice Python runtime (for example: /abs/path/.venv/bin/python).`,
    );
    process.exit(1);
  });

  child.on("exit", (code, signal) => {
    if (typeof code === "number") {
      process.exit(code);
    }
    if (signal) {
      process.kill(process.pid, signal);
      return;
    }
    process.exit(1);
  });
}

if (args.includes("--version") || args.includes("-v")) {
  console.log(version);
  process.exit(0);
}

if (args.length === 0 || args[0] === "--help" || args[0] === "-h") {
  console.log(`alice ${version}

Usage:
  alice hello
  alice brief [alicebot-args...]
  alice mcp [alicebot-mcp-args...]
  alice --help
  alice --version`);
  process.exit(0);
}

if (args[0] === "hello") {
  try {
    const { helloAlice } = await import("@aliceos/alice-core");
    console.log(helloAlice());
    process.exit(0);
  } catch (error) {
    console.error(
      `Failed to load @aliceos/alice-core: ${error.message}
Install dependencies with npm install.`,
    );
    process.exit(1);
  }
}

if (args[0] === "mcp") {
  forwardToPython("alicebot_api.mcp_server", args.slice(1), "Alice MCP server");
} else if (args[0] === "brief") {
  forwardToPython("alicebot_api", args, "Alice CLI");
} else {
  console.error(`Unknown command: ${args[0]}
Run "alice --help" for usage.`);
  process.exit(1);
}
