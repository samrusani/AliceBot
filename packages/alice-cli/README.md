# @aliceos/alice-cli

CLI package scaffold for AliceOS.

## Install

```bash
npm install -g @aliceos/alice-cli
```

## Usage

```bash
alice hello
alice mcp --help
alice --help
alice --version
```

## MCP passthrough

`alice mcp` launches the Python Alice MCP server:

```bash
ALICEBOT_PYTHON=/ABS/PATH/TO/AliceBot/.venv/bin/python alice mcp --help
```

For `npx` usage:

```bash
ALICEBOT_PYTHON=/ABS/PATH/TO/AliceBot/.venv/bin/python npx -y @aliceos/alice-cli mcp --help
```

Prerequisite: the selected Python runtime must be able to import
`alicebot_api.mcp_server` (for example, run from this repository after editable
install).
