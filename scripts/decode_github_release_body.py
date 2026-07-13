#!/usr/bin/env python3
"""Decode a GitHub Release JSON body without changing its text bytes."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def decode_release_body(payload: bytes) -> bytes:
    """Return the UTF-8 bytes represented by the payload's ``body`` string.

    GitHub's API transports a release body as a JSON string.  Decoding that
    string and writing it directly avoids the extra line feed that command-line
    JSON formatters append when printing a scalar value.
    """

    try:
        parsed: Any = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid GitHub Release JSON: {exc}") from exc
    if not isinstance(parsed, dict):
        raise ValueError("GitHub Release JSON must be an object")
    body = parsed.get("body")
    if not isinstance(body, str):
        raise ValueError("GitHub Release JSON field 'body' must be a string")
    try:
        return body.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise ValueError("GitHub Release body is not valid UTF-8 text") from exc


def write_decoded_release_body(*, input_path: Path, output_path: Path) -> None:
    """Decode ``input_path`` and write the exact represented body bytes."""

    output_path.write_bytes(decode_release_body(input_path.read_bytes()))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    write_decoded_release_body(input_path=args.input, output_path=args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
