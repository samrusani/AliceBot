"""README lead, committed demo vault, and the recorded GIF.

Each test names the edit that makes it fail. --data-dir and HOME are
tmp_path. Do not write ~/.alice. Do not OCR the GIF.
"""

from __future__ import annotations

from pathlib import Path

from alicebot_api.mcp_tools import AGENT_API_KEY_ENV
from alicebot_api.onramp import main as onramp_main
from alicebot_api.vnext_embeddings import (
    EMBEDDINGS_API_KEY_ENV,
    EMBEDDINGS_BASE_URL_ENV,
    EMBEDDINGS_MODEL_ENV,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
README_PATH = REPO_ROOT / "README.md"
VAULT_PATH = REPO_ROOT / "docs" / "examples" / "demo-vault"
GIF_PATH = REPO_ROOT / "docs" / "examples" / "alice-memory-demo.gif"
CANARY = "harbour-watch-29"
GIF_REF = "docs/examples/alice-memory-demo.gif"
PASTE_MARKERS = ("mcpServers", "mcp_servers", "mcp.servers")
GIF_HEADERS = (b"GIF87a", b"GIF89a")
MAX_GIF_BYTES = 3_000_000


def _first_twenty(readme: str) -> str:
    return "\n".join(readme.splitlines()[:20])


def _clear_env(monkeypatch) -> None:
    for env_name in (
        EMBEDDINGS_BASE_URL_ENV,
        EMBEDDINGS_MODEL_ENV,
        EMBEDDINGS_API_KEY_ENV,
        AGENT_API_KEY_ENV,
    ):
        monkeypatch.delenv(env_name, raising=False)


def test_readme_first_twenty_lines_name_install_and_demo_vault() -> None:
    """First twenty lines tell the reader to install, then demo a vault.

    Mutation: move those commands below line 20. This test fails.
    """

    lead = _first_twenty(README_PATH.read_text(encoding="utf-8"))
    assert "alice-memory install" in lead
    assert "demo --vault" in lead
    assert lead.index("alice-memory install") < lead.index("demo --vault")


def test_readme_first_twenty_lines_have_no_mcp_paste_or_unqualified_lme() -> None:
    """Lead has no MCP paste. 81.2% is not current product without the harness.

    Mutation: paste mcpServers above line 20, or put 81.2% in the first
    twenty lines without store_chunks / v0.12.0. This test fails.
    """

    lead = _first_twenty(README_PATH.read_text(encoding="utf-8"))
    for marker in PASTE_MARKERS:
        assert marker not in lead
    if "81.2" in lead:
        assert "store_chunks" in lead
        assert "v0.12.0" in lead


def test_committed_demo_vault_prints_will_quote_and_canary(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    """The committed harbour-watch vault quotes the canary.

    Mutation: empty the fixture. The demo fails.
    """

    _clear_env(monkeypatch)
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    data_dir = tmp_path / "demo-data"
    code = onramp_main(
        [
            "demo",
            "--vault",
            str(VAULT_PATH),
            "--data-dir",
            str(data_dir),
        ]
    )
    report = capsys.readouterr().out
    assert code == 0, report
    assert "will quote" in report
    assert CANARY in report
    assert not (home / ".alice").exists()
    assert (data_dir / "memory.db").is_file()


def test_committed_demo_gif_is_a_gif_and_in_the_readme_lead() -> None:
    """The committed GIF is a real GIF and the README lead points at it.

    Mutation: drop the file. This test fails.
    """

    assert GIF_PATH.is_file()
    header = GIF_PATH.read_bytes()[:6]
    assert header in GIF_HEADERS
    assert GIF_PATH.stat().st_size <= MAX_GIF_BYTES
    lead = _first_twenty(README_PATH.read_text(encoding="utf-8"))
    assert GIF_REF in lead
