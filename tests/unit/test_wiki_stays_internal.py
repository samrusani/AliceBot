"""The internal working wiki must never become a tracked file.

``wiki/`` holds working notes that are deliberately not published: unfixed
security detail, candid competitive assessment, and host operational specifics.
A ``.gitignore`` entry keeps it out of ``git add -A``, but an ignore rule is one
careless edit away from being deleted, and the failure is silent. These tests
fail loudly instead.

They assert absence rather than content, so they say nothing about what the
wiki contains and are safe to publish.
"""

from __future__ import annotations

from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[2]
WIKI_DIRECTORY = "wiki"


def _git(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ("git", "-C", str(ROOT), *arguments),
        capture_output=True,
        text=True,
        check=False,
    )


def test_no_wiki_file_is_tracked() -> None:
    """No file under ``wiki/`` may be in the index or any commit reachable now."""

    tracked = _git("ls-files", "--", WIKI_DIRECTORY)
    assert tracked.returncode == 0, tracked.stderr
    assert tracked.stdout.strip() == "", (
        "internal wiki files are tracked by git: "
        f"{tracked.stdout.strip().splitlines()}. Remove them with "
        "'git rm --cached' before committing; they are not for publication."
    )


def test_wiki_is_still_ignored() -> None:
    """The ignore rule itself must be present, not merely the absence of files.

    An empty ``wiki/`` directory would pass the tracking check above while the
    rule was gone, and the next note written would be stageable.
    """

    if not (ROOT / WIKI_DIRECTORY).exists():
        # Nothing to protect on a checkout that has no local wiki.
        return

    ignored = _git("check-ignore", "-q", f"{WIKI_DIRECTORY}/probe.md")
    assert ignored.returncode == 0, (
        f"'{WIKI_DIRECTORY}/' is no longer matched by .gitignore, so internal "
        "notes can be staged. Restore the rule."
    )


def test_wiki_is_absent_from_the_packaged_distribution() -> None:
    """Packaging must not reach the wiki even if the ignore rule is lost."""

    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert f'"{WIKI_DIRECTORY}"' not in pyproject
    assert f"{WIKI_DIRECTORY}/" not in pyproject
