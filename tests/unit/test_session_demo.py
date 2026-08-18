"""alice-memory demo --vault: import, doctor, brief, quote. No live-home write.

Put next to the session-doctor tests. Each test names the edit that makes it fail.
"""

from __future__ import annotations

import json
from pathlib import Path

from alicebot_api.mcp_tools import AGENT_API_KEY_ENV
from alicebot_api.onramp import (
    DEFAULT_DATA_DIR,
    DEFAULT_DEMO_DATA_DIR,
    _KNOWN_COMMANDS,
    _normalized_argv,
    build_parser,
    main as onramp_main,
    resolve_db_path,
)
from alicebot_api.sqlite_store import SQLiteVNextStore, ensure_sqlite_user, sqlite_user_connection
from alicebot_api.vault_demo import QUOTE_LABEL, SOURCE_LINE_PREFIX
from alicebot_api.vnext_embeddings import (
    EMBEDDINGS_API_KEY_ENV,
    EMBEDDINGS_BASE_URL_ENV,
    EMBEDDINGS_MODEL_ENV,
)

USER_ID = "00000000-0000-0000-0000-000000000001"
OTHER_USER_ID = "00000000-0000-0000-0000-000000000002"

SOURCE_SENTENCE = "The indigo-lighthouse-42 canary stays in the vault."
SOURCE_NOTE = f"# Vault canary\n\n{SOURCE_SENTENCE}\n"
VAULT_FILENAME = "indigo-lighthouse-42.md"

FORBIDDEN_PHRASES = ("review console", "/vnext", "clear the queue")
DEMO_VAULT_INVALID = {
    "error": {
        "code": "demo_vault_invalid",
        "message": "The demo vault is missing, is not a directory, or has no quotable markdown",
    }
}


def _clear_env(monkeypatch) -> None:
    for env_name in (
        EMBEDDINGS_BASE_URL_ENV,
        EMBEDDINGS_MODEL_ENV,
        EMBEDDINGS_API_KEY_ENV,
        AGENT_API_KEY_ENV,
    ):
        monkeypatch.delenv(env_name, raising=False)


def _write_vault(tmp_path: Path) -> Path:
    vault = tmp_path / "notes"
    vault.mkdir()
    (vault / VAULT_FILENAME).write_text(SOURCE_NOTE, encoding="utf-8")
    return vault


def _line_value(report: str, label: str) -> str:
    prefix = f"{label}: "
    for line in report.splitlines():
        if line.startswith(prefix):
            return line[len(prefix) :].strip()
    raise AssertionError(f"missing {label!r} in report:\n{report}")


def _int_value(report: str, label: str) -> int:
    return int(_line_value(report, label).split()[0])


def _error_records(stderr: str) -> list[object]:
    return [json.loads(line) for line in stderr.splitlines() if line.startswith("{")]


def _quote_line(report: str) -> str:
    prefix = f"{QUOTE_LABEL}: "
    for line in report.splitlines():
        if line.startswith(prefix):
            return line
    raise AssertionError(f"missing quote line in report:\n{report}")


def test_demo_missing_from_known_commands_becomes_mcp() -> None:
    """If demo is missing from _KNOWN_COMMANDS, argv handling fails like doctor.

    Mutation: drop ``demo`` from ``_KNOWN_COMMANDS``. This test fails.
    """

    assert "demo" in _KNOWN_COMMANDS
    assert _normalized_argv(["demo", "--vault", "/tmp/x"]) == [
        "demo",
        "--vault",
        "/tmp/x",
    ]
    assert _normalized_argv(["demo", "--vault", "/tmp/x"])[0] != "mcp"


def test_successful_demo_prints_doctor_brief_and_quote(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    """After a successful demo: sources and chunks, a source brief, and a quote.

    Mutation: skip the brief, skip the quote, auto-promote, or print a
    review-console sentence. This test fails.
    """

    _clear_env(monkeypatch)
    vault = _write_vault(tmp_path)
    data_dir = tmp_path / "demo-data"
    assert (
        onramp_main(
            [
                "demo",
                "--vault",
                str(vault),
                "--data-dir",
                str(data_dir),
                "--user-id",
                USER_ID,
            ]
        )
        == 0
    )
    report = capsys.readouterr().out

    assert _int_value(report, "imported") == 1
    assert _int_value(report, "duplicate") == 0
    assert _int_value(report, "failed") == 0
    assert _int_value(report, "sources") >= 1
    assert _int_value(report, "searchable chunks") >= 1
    assert _int_value(report, "committed facts") == 0
    assert SOURCE_LINE_PREFIX in report
    assert SOURCE_SENTENCE in _quote_line(report)
    assert report.index("imported:") < report.index("sources:")
    assert report.index("sources:") < report.index(SOURCE_LINE_PREFIX)
    assert report.index(SOURCE_LINE_PREFIX) < report.index(f"{QUOTE_LABEL}:")
    lowered = report.casefold()
    for phrase in FORBIDDEN_PHRASES:
        assert phrase.casefold() not in lowered, report


def test_omitted_data_dir_resolves_under_alice_demo_not_alice(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    """Omitted --data-dir must use ~/.alice-demo, never ~/.alice.

    Mutation: default the demo --data-dir to DEFAULT_DATA_DIR. This test fails.
    Never writes the owner's live vault. HOME is a tmp_path.
    """

    _clear_env(monkeypatch)
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setenv("HOME", str(fake_home))

    parser = build_parser()
    args = parser.parse_args(["demo", "--vault", str(tmp_path / "notes")])
    assert args.data_dir == DEFAULT_DEMO_DATA_DIR
    assert args.data_dir != DEFAULT_DATA_DIR
    assert DEFAULT_DEMO_DATA_DIR == "~/.alice-demo"
    assert DEFAULT_DEMO_DATA_DIR != DEFAULT_DATA_DIR

    resolved = resolve_db_path(data_dir=args.data_dir, db=None)
    live = resolve_db_path(data_dir=DEFAULT_DATA_DIR, db=None)
    assert resolved == (fake_home / ".alice-demo" / "memory.db").resolve()
    assert live == (fake_home / ".alice" / "memory.db").resolve()
    assert resolved != live

    vault = _write_vault(tmp_path)
    assert onramp_main(["demo", "--vault", str(vault), "--user-id", USER_ID]) == 0
    capsys.readouterr()
    assert (fake_home / ".alice-demo" / "memory.db").is_file()
    assert not (fake_home / ".alice").exists()


def test_second_user_and_live_home_are_not_written(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    """A second-user row must not change the acting user's census.

    Mutation: open the store without user_id, or write DEFAULT_DATA_DIR.
    This test fails. HOME is a tmp_path so the live vault is never touched.
    """

    _clear_env(monkeypatch)
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setenv("HOME", str(fake_home))

    vault = _write_vault(tmp_path)
    data_dir = tmp_path / "demo-data"
    argv = [
        "demo",
        "--vault",
        str(vault),
        "--data-dir",
        str(data_dir),
        "--user-id",
        USER_ID,
    ]
    assert onramp_main(argv) == 0
    before = capsys.readouterr().out
    before_counts = (
        _int_value(before, "sources"),
        _int_value(before, "searchable chunks"),
        _int_value(before, "committed facts"),
    )

    database = resolve_db_path(data_dir=str(data_dir), db=None)
    with sqlite_user_connection(database, OTHER_USER_ID) as connection:
        ensure_sqlite_user(connection, OTHER_USER_ID, "other@alice", "Other")
        store = SQLiteVNextStore(connection, OTHER_USER_ID)
        source = store.create_source(
            {
                "source_type": "note",
                "title": "Other user source",
                "content_hash": "other-user-demo-source-hash",
                "domain": "personal",
                "sensitivity": "private",
            }
        )
        store.create_source_chunk(
            {
                "source_id": source["id"],
                "chunk_index": 0,
                "text": "Other user chunk that must not appear in the first user's demo.",
            }
        )

    assert onramp_main(argv) == 0
    after = capsys.readouterr().out
    after_counts = (
        _int_value(after, "sources"),
        _int_value(after, "searchable chunks"),
        _int_value(after, "committed facts"),
    )
    assert after_counts == before_counts
    assert before_counts[0] >= 1
    assert before_counts[1] >= 1
    assert before_counts[2] == 0
    assert "Other user chunk" not in after
    assert not (fake_home / ".alice").exists()
    assert not (fake_home / ".alice-demo").exists()
    assert (data_dir / "memory.db").is_file()


def test_demo_stdout_does_not_send_anyone_to_review(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    """The demo must not name a review UI.

    Mutation: add ``review console``, ``/vnext``, or ``clear the queue``.
    This test fails.
    """

    _clear_env(monkeypatch)
    vault = _write_vault(tmp_path)
    assert (
        onramp_main(
            [
                "demo",
                "--vault",
                str(vault),
                "--data-dir",
                str(tmp_path / "demo-data"),
                "--user-id",
                USER_ID,
            ]
        )
        == 0
    )
    report = capsys.readouterr().out
    lowered = report.casefold()
    for phrase in FORBIDDEN_PHRASES:
        assert phrase.casefold() not in lowered, report


def test_empty_folder_or_missing_vault_exits_nonzero(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    """Empty folder, blank markdown, or missing --vault: no empty success.

    Mutation: treat an empty folder or whitespace-only *.md as success,
    make --vault optional, or print the caught exception. This test fails.
    """

    _clear_env(monkeypatch)
    data_dir = tmp_path / "demo-data"

    empty = tmp_path / "empty"
    empty.mkdir()
    empty_code = onramp_main(
        ["demo", "--vault", str(empty), "--data-dir", str(data_dir), "--user-id", USER_ID]
    )
    empty_err = capsys.readouterr().err
    assert empty_code != 0
    assert _error_records(empty_err) == [DEMO_VAULT_INVALID]
    assert str(empty) not in empty_err
    assert "Traceback" not in empty_err
    assert not (data_dir / "memory.db").exists()

    blank = tmp_path / "blank"
    blank.mkdir()
    (blank / "empty.md").write_text("\n\n  \n", encoding="utf-8")
    blank_code = onramp_main(
        ["demo", "--vault", str(blank), "--data-dir", str(data_dir), "--user-id", USER_ID]
    )
    blank_err = capsys.readouterr().err
    assert blank_code != 0
    assert _error_records(blank_err) == [DEMO_VAULT_INVALID]
    assert str(blank) not in blank_err
    assert not (data_dir / "memory.db").exists()

    missing_code = onramp_main(["demo", "--data-dir", str(data_dir), "--user-id", USER_ID])
    missing_err = capsys.readouterr().err
    assert missing_code != 0
    assert _error_records(missing_err) == [
        {
            "error": {
                "code": "invalid_request",
                "message": "The command request is invalid",
            }
        }
    ]

    missing_path = tmp_path / "does-not-exist"
    missing_path_code = onramp_main(
        [
            "demo",
            "--vault",
            str(missing_path),
            "--data-dir",
            str(data_dir),
            "--user-id",
            USER_ID,
        ]
    )
    missing_path_err = capsys.readouterr().err
    assert missing_path_code != 0
    assert _error_records(missing_path_err) == [DEMO_VAULT_INVALID]
    assert str(missing_path) not in missing_path_err

    note = tmp_path / "note.md"
    note.write_text(SOURCE_NOTE, encoding="utf-8")
    file_code = onramp_main(
        ["demo", "--vault", str(note), "--data-dir", str(data_dir), "--user-id", USER_ID]
    )
    file_err = capsys.readouterr().err
    assert file_code != 0
    assert _error_records(file_err) == [DEMO_VAULT_INVALID]
    assert str(note) not in file_err
    assert not (data_dir / "memory.db").exists()
