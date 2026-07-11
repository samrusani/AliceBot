#!/usr/bin/env python3
"""Fail-closed metadata, Git, and distribution checks for public releases."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
import re
import subprocess
import tarfile
import tomllib
from urllib.error import HTTPError
from urllib.request import Request, urlopen
import zipfile


ROOT_DIR = Path(__file__).resolve().parents[1]


@dataclass(frozen=True, slots=True)
class ReleaseMetadata:
    distribution_name: str
    version: str
    web_version: str

    @property
    def tag(self) -> str:
        return f"v{self.version}"


def _read_toml(path: Path) -> dict[str, object]:
    with path.open("rb") as handle:
        return tomllib.load(handle)


def read_release_metadata(root_dir: Path = ROOT_DIR) -> ReleaseMetadata:
    pyproject = _read_toml(root_dir / "pyproject.toml")
    project = pyproject.get("project")
    if not isinstance(project, dict):
        raise ValueError("pyproject.toml is missing [project]")
    distribution_name = str(project.get("name", ""))
    version = str(project.get("version", ""))

    web_payload = json.loads((root_dir / "apps" / "web" / "package.json").read_text(encoding="utf-8"))
    if not isinstance(web_payload, dict):
        raise ValueError("apps/web/package.json must contain an object")
    return ReleaseMetadata(
        distribution_name=distribution_name,
        version=version,
        web_version=str(web_payload.get("version", "")),
    )


def validate_metadata(root_dir: Path = ROOT_DIR) -> tuple[ReleaseMetadata, list[str]]:
    metadata = read_release_metadata(root_dir)
    issues: list[str] = []
    if metadata.distribution_name != "alice-memory":
        issues.append(f"unexpected distribution name: {metadata.distribution_name!r}")
    if not re.fullmatch(r"(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)", metadata.version):
        issues.append(f"release version must be stable SemVer, got {metadata.version!r}")
    if metadata.web_version != metadata.version:
        issues.append(
            "apps/web/package.json version does not match pyproject.toml: "
            f"{metadata.web_version!r} != {metadata.version!r}"
        )

    api_source = (root_dir / "apps" / "api" / "src" / "alicebot_api" / "main.py").read_text(encoding="utf-8")
    if 'FastAPI(title="AliceBot API", version=__version__)' not in api_source:
        issues.append("FastAPI application version is not sourced from alicebot_api.__version__")
    package_init = (
        root_dir / "apps" / "api" / "src" / "alicebot_api" / "__init__.py"
    ).read_text(encoding="utf-8")
    if '_distribution_version("alice-memory")' not in package_init:
        issues.append("alicebot_api.__version__ is not sourced from installed distribution metadata")
    return metadata, issues


def validate_release_document_state(
    root_dir: Path,
    *,
    version: str,
    require_finalized: bool,
) -> list[str]:
    if not require_finalized:
        return []

    issues: list[str] = []
    changelog = (root_dir / "CHANGELOG.md").read_text(encoding="utf-8")
    release_heading = re.compile(
        rf"^## v{re.escape(version)} — \d{{4}}-\d{{2}}-\d{{2}}$",
        flags=re.MULTILINE,
    )
    if release_heading.search(changelog) is None:
        issues.append(
            f"CHANGELOG.md must contain a finalized dated heading for v{version}"
        )
    unreleased_match = re.search(
        r"^## Unreleased\s*$\n(?P<body>.*?)(?=^##\s|\Z)",
        changelog,
        flags=re.MULTILINE | re.DOTALL,
    )
    if unreleased_match is None:
        issues.append("CHANGELOG.md must retain an empty Unreleased section")
    elif unreleased_match.group("body").strip():
        issues.append("CHANGELOG.md Unreleased section must be empty for the release tag")

    release_notes_path = root_dir / "docs" / "release" / f"v{version}-release-notes.md"
    try:
        release_notes = release_notes_path.read_text(encoding="utf-8")
    except OSError:
        issues.append(f"release notes are missing: {release_notes_path.relative_to(root_dir)}")
    else:
        expected_title = f"# Alice v{version} Release Notes"
        if not release_notes.startswith(expected_title + "\n"):
            issues.append(f"release notes must start with finalized title: {expected_title}")
        normalized_notes = release_notes.lower()
        stale_status_phrases = (
            "not published yet",
            "these notes describe the current candidate",
            "release is blocked until",
        )
        if any(phrase in normalized_notes for phrase in stale_status_phrases):
            issues.append("release notes still contain release-candidate status language")
    return issues


def _git(root_dir: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=root_dir,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def validate_git_state(
    *,
    root_dir: Path,
    tag: str | None,
    expected_sha: str | None,
    require_main_head: bool,
    require_clean: bool,
) -> list[str]:
    issues: list[str] = []
    head = _git(root_dir, "rev-parse", "HEAD")
    if expected_sha is not None and head != expected_sha:
        issues.append(f"checked-out SHA {head} does not match expected release SHA {expected_sha}")

    if tag is not None:
        tag_ref = f"refs/tags/{tag}"
        try:
            tag_type = _git(root_dir, "cat-file", "-t", tag_ref)
            tag_sha = _git(root_dir, "rev-list", "-n", "1", tag_ref)
        except subprocess.CalledProcessError:
            issues.append(f"release tag does not exist locally: {tag}")
        else:
            if tag_type != "tag":
                issues.append(f"release tag {tag} must be an annotated tag, got {tag_type}")
            if tag_sha != head:
                issues.append(f"release tag {tag} points to {tag_sha}, not checked-out SHA {head}")

    if require_main_head:
        try:
            main_sha = _git(root_dir, "rev-parse", "refs/remotes/origin/main")
        except subprocess.CalledProcessError:
            issues.append("origin/main is unavailable; fetch it before running the release check")
        else:
            if head != main_sha:
                issues.append(f"release SHA {head} is not the exact origin/main head {main_sha}")

    if require_clean and _git(root_dir, "status", "--porcelain"):
        issues.append("working tree is not clean")
    return issues


def _wheel_version(path: Path) -> str:
    with zipfile.ZipFile(path) as archive:
        metadata_names = [name for name in archive.namelist() if name.endswith(".dist-info/METADATA")]
        if len(metadata_names) != 1:
            raise ValueError(f"wheel must contain one METADATA file, found {metadata_names}")
        metadata_text = archive.read(metadata_names[0]).decode("utf-8")
    for line in metadata_text.splitlines():
        if line.startswith("Version: "):
            return line.removeprefix("Version: ").strip()
    raise ValueError("wheel METADATA is missing Version")


def _sdist_pyproject_version(path: Path) -> str:
    with tarfile.open(path, mode="r:gz") as archive:
        members = [member for member in archive.getmembers() if member.name.endswith("/pyproject.toml")]
        if len(members) != 1:
            raise ValueError(f"sdist must contain one pyproject.toml, found {[m.name for m in members]}")
        handle = archive.extractfile(members[0])
        if handle is None:
            raise ValueError("could not read sdist pyproject.toml")
        payload = tomllib.loads(handle.read().decode("utf-8"))
    project = payload.get("project")
    if not isinstance(project, dict):
        raise ValueError("sdist pyproject.toml is missing [project]")
    return str(project.get("version", ""))


def validate_distributions(dist_dir: Path, *, version: str) -> tuple[list[Path], list[str]]:
    wheels = sorted(dist_dir.glob("*.whl"))
    sdists = sorted(dist_dir.glob("*.tar.gz"))
    artifacts = [*wheels, *sdists]
    issues: list[str] = []
    if len(wheels) != 1:
        issues.append(f"expected exactly one wheel in {dist_dir}, found {[p.name for p in wheels]}")
    if len(sdists) != 1:
        issues.append(f"expected exactly one sdist in {dist_dir}, found {[p.name for p in sdists]}")
    if issues:
        return artifacts, issues

    wheel = wheels[0]
    sdist = sdists[0]
    try:
        if _wheel_version(wheel) != version:
            issues.append(f"wheel metadata version does not match {version}")
        if _sdist_pyproject_version(sdist) != version:
            issues.append(f"sdist metadata version does not match {version}")
    except (OSError, ValueError, tarfile.TarError, zipfile.BadZipFile) as exc:
        issues.append(f"could not inspect distributions: {exc}")
        return artifacts, issues

    required_wheel_resources = {
        "alicebot_api/_resources/alembic.ini",
        "alicebot_api/_resources/alembic/env.py",
        "alicebot_api/_resources/eval/public_eval_suites.json",
    }
    with zipfile.ZipFile(wheel) as archive:
        names = set(archive.namelist())
    missing = sorted(required_wheel_resources - names)
    if missing:
        issues.append(f"wheel is missing runtime resources: {missing}")
    if not any(
        name.startswith("alicebot_api/_resources/alembic/versions/") and name.endswith(".py")
        for name in names
    ):
        issues.append("wheel contains no packaged Alembic revisions")

    with tarfile.open(sdist, mode="r:gz") as archive:
        sdist_names = {member.name for member in archive.getmembers()}
    required_sdist_suffixes = (
        "/apps/api/alembic.ini",
        "/apps/api/alembic/env.py",
        "/eval/fixtures/public_eval_suites.json",
        "/setup.py",
    )
    for suffix in required_sdist_suffixes:
        if not any(name.endswith(suffix) for name in sdist_names):
            issues.append(f"sdist is missing build/runtime source: *{suffix}")
    return artifacts, issues


def write_checksums(dist_dir: Path, artifacts: list[Path]) -> Path:
    manifest = dist_dir / "SHA256SUMS"
    lines = [f"{sha256(path.read_bytes()).hexdigest()}  {path.name}" for path in sorted(artifacts)]
    manifest.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return manifest


def pypi_version_exists(distribution_name: str, version: str) -> bool:
    url = f"https://pypi.org/pypi/{distribution_name}/{version}/json"
    request = Request(url, headers={"User-Agent": "alice-release-check/1"})
    try:
        with urlopen(request, timeout=15) as response:  # noqa: S310 - fixed PyPI origin
            return response.status == 200
    except HTTPError as exc:
        if exc.code == 404:
            return False
        raise


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT_DIR)
    parser.add_argument("--tag", default=None, help="Release tag, for example v0.9.2.")
    parser.add_argument("--expected-sha", default=None)
    parser.add_argument("--require-main-head", action="store_true")
    parser.add_argument("--require-clean", action="store_true")
    parser.add_argument("--check-pypi", action="store_true")
    parser.add_argument(
        "--require-finalized-release-docs",
        action="store_true",
        help="Require a dated changelog section and final release-note title before tagging.",
    )
    parser.add_argument("--dist-dir", type=Path, default=None)
    parser.add_argument("--write-checksums", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root_dir = args.root.resolve()
    metadata, issues = validate_metadata(root_dir)

    if args.tag is not None and args.tag != metadata.tag:
        issues.append(f"release tag {args.tag!r} does not match package version tag {metadata.tag!r}")
    issues.extend(
        validate_release_document_state(
            root_dir,
            version=metadata.version,
            require_finalized=args.require_finalized_release_docs or args.tag is not None,
        )
    )
    issues.extend(
        validate_git_state(
            root_dir=root_dir,
            tag=args.tag,
            expected_sha=args.expected_sha,
            require_main_head=args.require_main_head,
            require_clean=args.require_clean,
        )
    )

    artifacts: list[Path] = []
    if args.dist_dir is not None:
        artifacts, artifact_issues = validate_distributions(args.dist_dir.resolve(), version=metadata.version)
        issues.extend(artifact_issues)
    elif args.write_checksums:
        issues.append("--write-checksums requires --dist-dir")

    if args.check_pypi and pypi_version_exists(metadata.distribution_name, metadata.version):
        issues.append(f"{metadata.distribution_name} {metadata.version} already exists on PyPI")

    if issues:
        print("Release check: FAIL")
        for issue in issues:
            print(f" - {issue}")
        return 1

    if args.write_checksums:
        manifest = write_checksums(args.dist_dir.resolve(), artifacts)
        print(f" - wrote: {manifest}")
    print(f"Release check: PASS ({metadata.distribution_name} {metadata.version})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
