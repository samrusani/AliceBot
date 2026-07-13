from __future__ import annotations

from hashlib import sha256
import io
import json
from pathlib import Path
import re
from urllib.error import HTTPError

import pytest

from scripts import (
    decode_github_release_body,
    prepare_mainprotect_update,
    release_check,
    render_release_body,
)
from scripts.check_github_release_checks import BRANCH_PROTECTION_REQUIRED_CHECKS


def test_render_release_body_uses_only_structured_publication_neutral_fields(
    tmp_path: Path,
) -> None:
    checksums = tmp_path / "SHA256SUMS"
    checksums.write_text(
        f"{'a' * 64}  alice_memory-1.2.3-py3-none-any.whl\n"
        f"{'b' * 64}  alice_memory-1.2.3.tar.gz\n",
        encoding="utf-8",
    )

    body = render_release_body.render_release_body(
        repository="owner/repo",
        tag="v1.2.3",
        commit_sha="c" * 40,
        checksum_manifest=checksums,
    )

    assert "Alice v1.2.3" in body
    assert "sha256:" + "a" * 64 in body
    assert "https://pypi.org/project/alice-memory/1.2.3/" in body
    assert "will be published" not in body
    assert "candidate" not in body.casefold()
    assert body.endswith("\n")
    assert not body.endswith("\n\n")


def test_render_release_body_rejects_noncanonical_checksum_lines(tmp_path: Path) -> None:
    checksums = tmp_path / "SHA256SUMS"
    checksums.write_text("not-a-checksum\n", encoding="utf-8")

    with pytest.raises(ValueError, match="invalid checksum manifest"):
        render_release_body.render_release_body(
            repository="owner/repo",
            tag="v1.2.3",
            commit_sha="c" * 40,
            checksum_manifest=checksums,
        )


def test_release_body_json_decode_preserves_exact_utf8_and_single_trailing_lf() -> None:
    body = "Alice v1.2.3\n\nUnicode: café — ready\n"
    payload = json.dumps({"body": body}, ensure_ascii=True).encode("utf-8") + b"\n"

    decoded = decode_github_release_body.decode_release_body(payload)

    assert decoded == body.encode("utf-8")
    assert decoded.endswith(b"\n")
    assert not decoded.endswith(b"\n\n")


@pytest.mark.parametrize("body", ("no trailing line feed", "two\n\n"))
def test_release_body_json_decode_never_normalizes_line_endings(body: str) -> None:
    payload = json.dumps({"body": body}).encode("utf-8")

    assert decode_github_release_body.decode_release_body(payload) == body.encode("utf-8")


@pytest.mark.parametrize(
    "payload",
    (
        b"not-json",
        b"[]",
        b'{"body":null}',
    ),
)
def test_release_body_json_decode_rejects_invalid_payloads(payload: bytes) -> None:
    with pytest.raises(ValueError):
        decode_github_release_body.decode_release_body(payload)


def _workflow_job(workflow: str, job_name: str) -> str:
    match = re.search(
        rf"(?ms)^  {re.escape(job_name)}:\n.*?(?=^  [A-Za-z0-9_-]+:\n|\Z)",
        workflow,
    )
    assert match is not None
    return match.group(0)


def _assert_exact_body_readback(job: str) -> None:
    fetch = (
        'gh release view "$RELEASE_TAG" --repo "$GITHUB_REPOSITORY" '
        "--json body > /tmp/alice-current-release.json"
    )
    decode = (
        "python scripts/decode_github_release_body.py "
        "--input /tmp/alice-current-release.json "
        "--output /tmp/alice-current-release-body.md"
    )
    compare = "cmp /tmp/alice-release-body.md /tmp/alice-current-release-body.md"
    assert job.index(fetch) < job.index(decode) < job.index(compare)


def test_publish_mode_validates_exact_body_before_pypi_and_during_finalize() -> None:
    workflow = (Path(__file__).resolve().parents[2] / ".github/workflows/publish-pypi.yml").read_text(
        encoding="utf-8"
    )

    _assert_exact_body_readback(_workflow_job(workflow, "stage-github-draft"))
    _assert_exact_body_readback(_workflow_job(workflow, "finalize-github-release"))
    assert "needs: stage-github-draft" in _workflow_job(workflow, "publish")
    assert "--jq .body >" not in workflow


def test_finalize_existing_draft_mode_validates_exact_body_during_recovery() -> None:
    workflow = (Path(__file__).resolve().parents[2] / ".github/workflows/publish-pypi.yml").read_text(
        encoding="utf-8"
    )
    recovery = _workflow_job(workflow, "recover-github-release")

    assert "inputs.publication_mode != 'publish'" in recovery
    _assert_exact_body_readback(recovery)


def test_resume_pypi_mode_validates_exact_body_before_and_after_pypi() -> None:
    workflow = (Path(__file__).resolve().parents[2] / ".github/workflows/publish-pypi.yml").read_text(
        encoding="utf-8"
    )

    _assert_exact_body_readback(_workflow_job(workflow, "verify-resume-artifacts"))
    assert "needs: verify-resume-artifacts" in _workflow_job(workflow, "resume-pypi")
    _assert_exact_body_readback(_workflow_job(workflow, "recover-github-release"))


@pytest.mark.parametrize(
    ("job_name", "expected_commands"),
    (
        (
            "finalize-github-release",
            (
                'python scripts/release_check.py --tag "$RELEASE_TAG" '
                "--dist-dir verified --verify-release-assets --verify-pypi-artifacts",
            ),
        ),
        (
            "verify-resume-artifacts",
            (
                'python scripts/release_check.py --tag "$RELEASE_TAG" '
                "--dist-dir verified --verify-release-assets --verify-pypi-artifact-subset",
                'python scripts/release_check.py --tag "$RELEASE_TAG" '
                "--dist-dir verified --compare-dist-dir deterministic-rebuild "
                "--verify-release-assets --verify-pypi-artifact-subset",
            ),
        ),
        (
            "recover-github-release",
            (
                'python scripts/release_check.py --tag "$RELEASE_TAG" '
                "--dist-dir verified --verify-release-assets --verify-pypi-artifacts",
            ),
        ),
    ),
)
def test_release_finalization_and_recovery_checks_bind_requested_tag(
    job_name: str, expected_commands: tuple[str, ...]
) -> None:
    workflow = (Path(__file__).resolve().parents[2] / ".github/workflows/publish-pypi.yml").read_text(
        encoding="utf-8"
    )
    job = _workflow_job(workflow, job_name)
    commands = tuple(
        line.strip()
        for line in job.splitlines()
        if line.strip().startswith("python scripts/release_check.py")
    )

    assert commands == expected_commands


def test_normal_and_recovery_builds_pin_the_same_frontend_version() -> None:
    workflow = (Path(__file__).resolve().parents[2] / ".github/workflows/publish-pypi.yml").read_text(
        encoding="utf-8"
    )

    assert workflow.count("python -m pip install build==1.5.0") == 2
    assert "python -m build --outdir dist" in _workflow_job(workflow, "build-and-verify")
    assert "python -m build --outdir deterministic-rebuild" in _workflow_job(
        workflow, "verify-resume-artifacts"
    )


def test_prepare_mainprotect_update_replaces_only_required_contexts() -> None:
    current = {
        "id": 42,
        "name": "MainProtect",
        "target": "branch",
        "source": "owner/repo",
        "enforcement": "active",
        "bypass_actors": [
            {"actor_id": 5, "actor_type": "RepositoryRole", "bypass_mode": "always"}
        ],
        "conditions": {
            "ref_name": {"include": ["~DEFAULT_BRANCH"], "exclude": []}
        },
        "rules": [
            {"type": "deletion"},
            {
                "type": "required_status_checks",
                "parameters": {
                    "required_status_checks": [
                        {"context": "Web tests, lint, build"}
                    ],
                    "strict_required_status_checks_policy": False,
                },
            },
        ],
    }

    payload = prepare_mainprotect_update.prepare_mainprotect_update(current)

    assert "id" not in payload
    assert payload["bypass_actors"] == current["bypass_actors"]
    assert {rule["type"] for rule in payload["rules"]} == {
        "deletion",
        "required_status_checks",
    }
    status_rule = next(
        rule for rule in payload["rules"] if rule["type"] == "required_status_checks"
    )
    assert status_rule["parameters"] == {
        "required_status_checks": [
            {"context": context} for context in BRANCH_PROTECTION_REQUIRED_CHECKS
        ],
        "strict_required_status_checks_policy": True,
    }


def test_verify_pypi_artifacts_matches_exact_file_set_and_hashes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    wheel = tmp_path / "alice_memory-1.2.3-py3-none-any.whl"
    sdist = tmp_path / "alice_memory-1.2.3.tar.gz"
    wheel.write_bytes(b"wheel")
    sdist.write_bytes(b"sdist")
    payload = {
        "urls": [
            {
                "filename": wheel.name,
                "digests": {"sha256": sha256(wheel.read_bytes()).hexdigest()},
            },
            {
                "filename": sdist.name,
                "digests": {"sha256": sha256(sdist.read_bytes()).hexdigest()},
            },
        ]
    }
    monkeypatch.setattr(
        release_check,
        "urlopen",
        lambda *_args, **_kwargs: io.BytesIO(json.dumps(payload).encode("utf-8")),
    )

    assert release_check.verify_pypi_artifacts(
        distribution_name="alice-memory",
        version="1.2.3",
        artifacts=[wheel, sdist],
    ) == []

    payload["urls"][0]["digests"]["sha256"] = "0" * 64
    issues = release_check.verify_pypi_artifacts(
        distribution_name="alice-memory",
        version="1.2.3",
        artifacts=[wheel, sdist],
    )
    assert issues == [f"PyPI sha256 does not match verified artifact {wheel.name}"]


def test_release_asset_set_requires_exact_manifest_and_rejects_extras(
    tmp_path: Path,
) -> None:
    wheel = tmp_path / "alice_memory-1.2.3-py3-none-any.whl"
    sdist = tmp_path / "alice_memory-1.2.3.tar.gz"
    wheel.write_bytes(b"wheel")
    sdist.write_bytes(b"sdist")
    (tmp_path / "SHA256SUMS").write_text(
        f"{sha256(wheel.read_bytes()).hexdigest()}  {wheel.name}\n"
        f"{sha256(sdist.read_bytes()).hexdigest()}  {sdist.name}\n",
        encoding="utf-8",
    )

    assert release_check.validate_release_asset_set(
        dist_dir=tmp_path, artifacts=[wheel, sdist]
    ) == []

    (tmp_path / "unverified.txt").write_text("extra", encoding="utf-8")
    issues = release_check.validate_release_asset_set(
        dist_dir=tmp_path, artifacts=[wheel, sdist]
    )
    assert any("release asset set" in issue for issue in issues)


def test_pypi_subset_verification_allows_only_matching_partial_upload(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    wheel = tmp_path / "alice_memory-1.2.3-py3-none-any.whl"
    sdist = tmp_path / "alice_memory-1.2.3.tar.gz"
    wheel.write_bytes(b"wheel")
    sdist.write_bytes(b"sdist")
    payload = {
        "urls": [
            {
                "filename": wheel.name,
                "digests": {"sha256": sha256(wheel.read_bytes()).hexdigest()},
            }
        ]
    }
    monkeypatch.setattr(
        release_check,
        "urlopen",
        lambda *_args, **_kwargs: io.BytesIO(json.dumps(payload).encode("utf-8")),
    )

    assert release_check.verify_pypi_artifacts(
        distribution_name="alice-memory",
        version="1.2.3",
        artifacts=[wheel, sdist],
        allow_subset=True,
    ) == []
    assert any(
        "not an exact permitted set" in issue
        for issue in release_check.verify_pypi_artifacts(
            distribution_name="alice-memory",
            version="1.2.3",
            artifacts=[wheel, sdist],
        )
    )


@pytest.mark.parametrize("pypi_state", ("missing", "empty", "complete"))
def test_pypi_resume_rejects_nonpartial_states(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, pypi_state: str
) -> None:
    wheel = tmp_path / "alice_memory-1.2.3-py3-none-any.whl"
    sdist = tmp_path / "alice_memory-1.2.3.tar.gz"
    wheel.write_bytes(b"wheel")
    sdist.write_bytes(b"sdist")
    files = [wheel, sdist]

    if pypi_state == "missing":
        def missing(*_args: object, **_kwargs: object) -> io.BytesIO:
            raise HTTPError("https://pypi.org", 404, "missing", {}, None)

        monkeypatch.setattr(release_check, "urlopen", missing)
    else:
        published_files = [] if pypi_state == "empty" else files
        payload = {
            "urls": [
                {
                    "filename": path.name,
                    "digests": {"sha256": sha256(path.read_bytes()).hexdigest()},
                }
                for path in published_files
            ]
        }
        monkeypatch.setattr(
            release_check,
            "urlopen",
            lambda *_args, **_kwargs: io.BytesIO(json.dumps(payload).encode("utf-8")),
        )

    issues = release_check.verify_pypi_artifacts(
        distribution_name="alice-memory",
        version="1.2.3",
        artifacts=files,
        allow_subset=True,
    )

    assert issues
    assert any(
        marker in issue
        for issue in issues
        for marker in ("does not exist", "at least one", "proper partial")
    )


def test_deterministic_rebuild_rejects_replaced_unpublished_distribution(
    tmp_path: Path,
) -> None:
    canonical_dir = tmp_path / "canonical"
    rebuilt_dir = tmp_path / "rebuilt"
    canonical_dir.mkdir()
    rebuilt_dir.mkdir()
    canonical = [
        canonical_dir / "alice_memory-1.2.3-py3-none-any.whl",
        canonical_dir / "alice_memory-1.2.3.tar.gz",
    ]
    rebuilt = [rebuilt_dir / path.name for path in canonical]
    for path, content in zip(canonical, (b"wheel", b"sdist"), strict=True):
        path.write_bytes(content)
    for path, content in zip(rebuilt, (b"wheel", b"sdist"), strict=True):
        path.write_bytes(content)

    assert release_check.compare_distribution_artifacts(
        canonical=canonical, rebuilt=rebuilt
    ) == []

    canonical[1].write_bytes(b"replaced unpublished sdist")
    assert release_check.compare_distribution_artifacts(
        canonical=canonical, rebuilt=rebuilt
    ) == [
        "deterministic rebuild does not match canonical artifact "
        "alice_memory-1.2.3.tar.gz"
    ]
