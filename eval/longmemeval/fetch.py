"""Download the LongMemEval dataset into ``eval/longmemeval/data/``.

Canonical source (July 2026): the ``xiaowu0162/longmemeval-cleaned``
HuggingFace dataset repo — the official repo README points here since the
2025/09 cleanup of the history sessions. The HuggingFace ``datasets`` loader
does not work on these files (mixed str/int ``answer`` column), and the
package is not installed in this repo's venv anyway, so this fetcher streams
the raw JSON files over plain HTTPS (stdlib ``urllib``) and verifies the
SHA-256 digests published by the HuggingFace LFS API.

Usage (from the repo root):

    .venv/bin/python eval/longmemeval/fetch.py --variant s
    .venv/bin/python eval/longmemeval/fetch.py --variant oracle --check

Files are written to ``eval/longmemeval/data/`` (gitignored; never commit).
"""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import shutil
import sys
import tempfile
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

_EVAL_DIR = Path(__file__).resolve().parent.parent
if str(_EVAL_DIR) not in sys.path:  # direct execution: python eval/longmemeval/fetch.py
    sys.path.insert(0, str(_EVAL_DIR))

from longmemeval.dataset import DATA_DIR, VARIANTS, preferred_dataset_filename, resolve_dataset_path  # noqa: E402


BASE_URL = "https://huggingface.co/datasets/xiaowu0162/longmemeval-cleaned/resolve/main"
_CHUNK_BYTES = 1 << 20
_USER_AGENT = "alicebot-longmemeval-harness/1.0"

# Size and SHA-256 per file, as published by the HuggingFace LFS tree API
# (https://huggingface.co/api/datasets/xiaowu0162/longmemeval-cleaned/tree/main),
# recorded 2026-07-04.
EXPECTED_FILES: dict[str, tuple[int, str]] = {
    "longmemeval_s_cleaned.json": (
        277_383_467,
        "d6f21ea9d60a0d56f34a05b609c79c88a451d2ae03597821ea3d5a9678c3a442",
    ),
    "longmemeval_m_cleaned.json": (
        2_737_100_077,
        "9d79e5524794a2e6900a3aa9cb7d9152c5a3e8319c9a87c25494ba1eacee495f",
    ),
    "longmemeval_oracle.json": (
        15_388_478,
        "821a2034d219ab45846873dd14c14f12cfe7776e73527a483f9dac095d38620c",
    ),
}


class LongMemEvalFetchError(RuntimeError):
    """Raised when a download fails or a checksum does not match."""


def sha256_of_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(_CHUNK_BYTES), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_file(path: Path, *, expected_sha256: str | None) -> str:
    actual = sha256_of_file(path)
    if expected_sha256 is not None and actual != expected_sha256:
        raise LongMemEvalFetchError(
            f"checksum mismatch for {path.name}: expected {expected_sha256}, got {actual}; "
            "delete the file and re-run the fetch"
        )
    return actual


def download_variant(variant: str, *, data_dir: Path = DATA_DIR, force: bool = False) -> Path:
    filename = preferred_dataset_filename(variant)
    expected_size, expected_sha256 = EXPECTED_FILES[filename]
    data_dir.mkdir(parents=True, exist_ok=True)
    target = data_dir / filename

    if target.is_file() and not force:
        print(f"[fetch] {filename} already present; verifying checksum ...", flush=True)
        verify_file(target, expected_sha256=expected_sha256)
        print(f"[fetch] {filename} OK ({target.stat().st_size:,} bytes)")
        return target

    url = f"{BASE_URL}/{filename}"
    print(f"[fetch] downloading {url} ({expected_size:,} bytes expected) ...", flush=True)
    digest = hashlib.sha256()
    request = Request(url, headers={"User-Agent": _USER_AGENT})
    try:
        with urlopen(request) as response, tempfile.NamedTemporaryFile(
            dir=data_dir, prefix=f".{filename}.", suffix=".part", delete=False
        ) as part:
            part_path = Path(part.name)
            downloaded = 0
            while True:
                block = response.read(_CHUNK_BYTES)
                if not block:
                    break
                part.write(block)
                digest.update(block)
                downloaded += len(block)
                if downloaded % (64 * _CHUNK_BYTES) < _CHUNK_BYTES:
                    print(f"[fetch] ... {downloaded:,} / {expected_size:,} bytes", flush=True)
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        raise LongMemEvalFetchError(
            f"download failed for {url}: {exc}. If the network blocks HuggingFace, download the file "
            f"manually and place it at {target}"
        ) from exc

    actual = digest.hexdigest()
    if actual != expected_sha256:
        part_path.unlink(missing_ok=True)
        raise LongMemEvalFetchError(
            f"checksum mismatch after download of {filename}: expected {expected_sha256}, got {actual}"
        )
    shutil.move(str(part_path), target)
    print(f"[fetch] wrote {target} ({downloaded:,} bytes, sha256 verified)")
    return target


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Fetch the LongMemEval dataset (never committed to git).")
    parser.add_argument("--variant", choices=VARIANTS, default="s", help="dataset variant to fetch (default: s)")
    parser.add_argument("--data-dir", type=Path, default=DATA_DIR, help="download directory (default: eval/longmemeval/data)")
    parser.add_argument("--force", action="store_true", help="re-download even if the file exists")
    parser.add_argument("--check", action="store_true", help="only verify an already-downloaded file")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    if args.check:
        existing = resolve_dataset_path(args.variant, data_dir=args.data_dir)
        if existing is None:
            print(f"[fetch] no local file for variant {args.variant!r} under {args.data_dir}", file=sys.stderr)
            return 1
        expected = EXPECTED_FILES.get(existing.name, (None, None))[1]
        actual = verify_file(existing, expected_sha256=expected)
        suffix = "matches published sha256" if expected else f"sha256 {actual} (no published checksum for this name)"
        print(f"[fetch] {existing} OK: {suffix}")
        return 0
    try:
        download_variant(args.variant, data_dir=args.data_dir, force=args.force)
    except LongMemEvalFetchError as exc:
        print(f"[fetch] error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "BASE_URL",
    "EXPECTED_FILES",
    "LongMemEvalFetchError",
    "download_variant",
    "main",
    "sha256_of_file",
    "verify_file",
]
