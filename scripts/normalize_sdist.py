#!/usr/bin/env python3
"""Normalize tar metadata and gzip headers in built source distributions."""

from __future__ import annotations

import argparse
from copy import copy
import gzip
from io import BytesIO
from pathlib import Path
import tarfile


def normalize_gzip_timestamp(path: Path, *, source_date_epoch: int) -> None:
    if not 0 <= source_date_epoch <= 0xFFFFFFFF:
        raise ValueError("source date epoch is outside the gzip timestamp range")
    source_payload = path.read_bytes()
    source = BytesIO(source_payload)
    normalized_tar = BytesIO()
    try:
        with tarfile.open(fileobj=source, mode="r:gz") as input_tar:
            with tarfile.open(
                fileobj=normalized_tar, mode="w", format=tarfile.PAX_FORMAT
            ) as output_tar:
                for member in sorted(input_tar.getmembers(), key=lambda item: item.name):
                    normalized = copy(member)
                    normalized.mtime = source_date_epoch
                    normalized.uid = 0
                    normalized.gid = 0
                    normalized.uname = ""
                    normalized.gname = ""
                    normalized.pax_headers = {}
                    fileobj = input_tar.extractfile(member) if member.isfile() else None
                    output_tar.addfile(normalized, fileobj=fileobj)
    except (tarfile.TarError, OSError) as exc:
        raise ValueError(f"not a valid gzip-compressed source distribution: {path}") from exc
    path.write_bytes(
        gzip.compress(
            normalized_tar.getvalue(), compresslevel=9, mtime=source_date_epoch
        )
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--source-date-epoch", type=int, required=True)
    args = parser.parse_args()
    try:
        normalize_gzip_timestamp(
            args.archive, source_date_epoch=args.source_date_epoch
        )
    except (OSError, ValueError) as exc:
        print(f"Source-distribution normalization: FAIL\n - {exc}")
        return 1
    print(f"Source-distribution normalization: PASS ({args.archive})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
