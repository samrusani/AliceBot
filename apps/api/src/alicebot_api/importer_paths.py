"""Filesystem containment for importer source trees.

Importers walk a root the operator selected and read whatever they find under
it. Two ordinary habits break that boundary. ``Path.rglob`` descends directory
symlinks and ``Path.is_file`` is true for a link whose target is a regular
file, so one link planted inside the root can pull in bytes from anywhere the
server process can read. And re-opening a listed path for each pass lets the
name be swapped between passes, so the bytes that get archived as evidence
need not be the bytes that were parsed.

Everything here refuses to follow a link out of the selected root, and hands
back the exact text it read so callers parse and archive one snapshot.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
import errno
import fcntl
import os
from pathlib import Path
import stat


ErrorFactory = Callable[[str], Exception]

# BSD kernels report O_NOFOLLOW on a symlink as EMLINK rather than ELOOP.
_SYMLINK_OPEN_ERRNOS = frozenset({errno.ELOOP, errno.EMLINK})


@dataclass(frozen=True, slots=True)
class ImportSourceFile:
    """One import file opened once, with the bytes that were read."""

    path: Path
    relative_path: str
    text: str


def _relative_source_file(source_root: Path, file_path: Path) -> str:
    if source_root.is_dir():
        return str(file_path.relative_to(source_root))
    return file_path.name


def contained_source_files(
    source_root: Path,
    *,
    suffixes: Iterable[str],
    recursive: bool,
    error_factory: ErrorFactory,
) -> list[Path]:
    """List import candidates under ``source_root`` without following links.

    Walks with ``followlinks=False`` so no directory symlink is descended, and
    refuses any symlinked directory or candidate file instead of silently
    importing bytes from outside the root or silently skipping content the
    operator expected to import.
    """

    matches: list[Path] = []
    normalized_suffixes = {suffix.casefold() for suffix in suffixes}
    for raw_directory, directory_names, file_names in os.walk(source_root, followlinks=False):
        current_directory = Path(raw_directory)
        if recursive:
            for directory_name in sorted(directory_names):
                candidate_directory = current_directory / directory_name
                if candidate_directory.is_symlink():
                    raise error_factory(
                        f"import source must not contain symlinked directories: {candidate_directory}"
                    )
        for file_name in sorted(file_names):
            candidate = current_directory / file_name
            if candidate.suffix.casefold() not in normalized_suffixes:
                continue
            if candidate.is_symlink():
                raise error_factory(f"import source must not contain symlinked files: {candidate}")
            matches.append(candidate)
        if not recursive:
            directory_names[:] = []
    return sorted(matches)


def read_contained_source_text(
    file_path: Path,
    *,
    source_root: Path | None = None,
    error_factory: ErrorFactory,
) -> str:
    """Open one import file once and return the exact text that was read.

    ``O_NOFOLLOW`` fails the open when the final path component is a symlink,
    so a link swapped in after the listing cannot redirect the read.
    ``O_NONBLOCK`` keeps the open itself from parking forever on a FIFO that
    has no writer: the descriptor is checked to be a regular file before any
    bytes are consumed, and that check is worthless if the process never gets
    to it. The flag is cleared once the descriptor is known to be a regular
    file, for which it has no defined effect anyway.

    ``source_root``, when given, is enforced: a candidate carrying ``..`` or
    otherwise resolving outside the selected root is refused rather than read.

    Known limitation: a hard link is not a reference to a file, it is the
    file, so a hard link planted inside the root to content elsewhere is
    indistinguishable from ordinary content and is read. Nothing at this layer
    can separate the two.
    """

    if ".." in file_path.parts:
        raise error_factory(f"import source path must not traverse upward: {file_path}")
    if source_root is not None and not file_path.is_relative_to(source_root):
        raise error_factory(f"import source path escapes the selected root: {file_path}")

    open_flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    try:
        descriptor = os.open(file_path, open_flags)
    except OSError as exc:
        if exc.errno in _SYMLINK_OPEN_ERRNOS:
            raise error_factory(
                f"import source must not contain symlinked files: {file_path}"
            ) from exc
        raise error_factory(f"import source file is not readable: {file_path}") from exc

    try:
        # Checked on the descriptor rather than the path, so a swap between the
        # listing and the open cannot change what is measured. Without this a
        # FIFO under the root imports as an empty document, and on a platform
        # where the read-open parks, it hangs the import instead.
        opened_status = os.fstat(descriptor)
        if not stat.S_ISREG(opened_status.st_mode):
            raise error_factory(
                f"import source file is not a regular file: {file_path}"
            )
        descriptor_flags = fcntl.fcntl(descriptor, fcntl.F_GETFL)
        fcntl.fcntl(descriptor, fcntl.F_SETFL, descriptor_flags & ~os.O_NONBLOCK)
    except BaseException:
        os.close(descriptor)
        raise

    with os.fdopen(descriptor, "r", encoding="utf-8") as stream:
        try:
            return stream.read()
        except UnicodeDecodeError as exc:
            # Decoding is part of reading the file, so a bad byte has to leave
            # as the caller's own validation error naming the file. Raised bare
            # it surfaces as a byte offset with no path attached, which tells an
            # operator nothing about which file to go and look at.
            raise error_factory(
                f"import source file is not valid UTF-8 text: {file_path}"
            ) from exc


def snapshot_source_files(
    source_root: Path,
    files: Iterable[Path],
    *,
    error_factory: ErrorFactory,
) -> list[ImportSourceFile]:
    """Read every selected file once, in listing order."""

    return [
        ImportSourceFile(
            path=file_path,
            relative_path=_relative_source_file(source_root, file_path),
            text=read_contained_source_text(
                file_path,
                source_root=source_root,
                error_factory=error_factory,
            ),
        )
        for file_path in files
    ]


__all__ = [
    "ImportSourceFile",
    "contained_source_files",
    "read_contained_source_text",
    "snapshot_source_files",
]
