"""A host's ``PYTHONPATH`` must not shadow the dependencies we installed.

Reported from a real Hermes install on 2026-08-15, and reproduced here: `uvx`
installs Alice into an isolated environment, but Python still honours
``PYTHONPATH`` from the parent process and puts those entries near the front of
``sys.path``. A host launched from inside a conda environment or a virtualenv
leaks its own site-packages in, and a NumPy built for a different Python ABI
shadows ours. `alice-memory mcp` then dies on startup, before serving anything.

The user's agent worked around it by unsetting ``PYTHONPATH``, ``VIRTUAL_ENV``
and ``CONDA_PREFIX`` before launching. Nobody should have to know that, which is
why the fix lives in ``alicebot_api.__init__`` rather than in the docs. It has
to be in ``__init__`` specifically: ``onramp`` imports ``sqlite_store`` at module
scope and that imports NumPy, so by the time any ``main()`` runs it is too late.

The fix reorders ``sys.path`` and never removes an entry, so anything the host
provides that we do not ship still resolves.
"""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import textwrap

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
PACKAGE_SOURCE_ROOT = REPO_ROOT / "apps" / "api" / "src"


def _build_shadowed_layout(tmp_path: Path) -> tuple[Path, Path]:
    """A foreign dir whose `probe_dependency` explodes, and our own that works."""

    foreign = tmp_path / "foreign-site-packages"
    (foreign / "probe_dependency").mkdir(parents=True)
    (foreign / "probe_dependency" / "__init__.py").write_text(
        'raise ImportError("foreign build loaded: wrong ABI for this interpreter")\n',
        encoding="utf-8",
    )

    ours = tmp_path / "our-site-packages"
    ours.mkdir()
    # A stand-in for the real package, so the test does not depend on a build.
    (ours / "alicebot_api").mkdir()
    (ours / "alicebot_api" / "__init__.py").write_text(
        (PACKAGE_SOURCE_ROOT / "alicebot_api" / "__init__.py").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (ours / "probe_dependency").mkdir()
    (ours / "probe_dependency" / "__init__.py").write_text(
        "CORRECT_BUILD = True\n", encoding="utf-8"
    )
    return foreign, ours


def _run(script: str, *, pythonpath: str, ours: Path, foreign: Path) -> subprocess.CompletedProcess:
    environment = dict(os.environ)
    environment["PYTHONPATH"] = pythonpath
    # Keep the child from inheriting a pytest-shaped sys.path.
    environment.pop("PYTEST_CURRENT_TEST", None)
    return subprocess.run(
        [sys.executable, "-c", script.format(ours=str(ours), foreign=str(foreign))],
        capture_output=True,
        text=True,
        env=environment,
        timeout=60,
    )


_PLACE_OURS_AFTER_FOREIGN = """
import os, sys
foreign = os.path.abspath({foreign!r})
index = next(
    position for position, entry in enumerate(sys.path)
    if os.path.abspath(entry) == foreign
)
sys.path.insert(index + 1, {ours!r})
"""


def test_the_shadowing_actually_reproduces_without_the_fix(tmp_path: Path) -> None:
    """Guards the guard. If this stops failing, the test below proves nothing."""

    foreign, ours = _build_shadowed_layout(tmp_path)
    result = _run(
        _PLACE_OURS_AFTER_FOREIGN + """
import probe_dependency
print("imported", probe_dependency.__file__)
""",
        pythonpath=str(foreign),
        ours=ours,
        foreign=foreign,
    )

    assert result.returncode != 0, "the foreign build no longer shadows; this test is vacuous"
    assert "foreign build loaded" in result.stderr


def test_importing_alicebot_api_restores_our_own_dependency(tmp_path: Path) -> None:
    foreign, ours = _build_shadowed_layout(tmp_path)
    result = _run(
        _PLACE_OURS_AFTER_FOREIGN + """
import alicebot_api  # the fix runs on import
import probe_dependency
print("CORRECT_BUILD", getattr(probe_dependency, "CORRECT_BUILD", False))
""",
        pythonpath=str(foreign),
        ours=ours,
        foreign=foreign,
    )

    assert result.returncode == 0, f"import still failed:\n{result.stderr}"
    assert "CORRECT_BUILD True" in result.stdout


def test_a_deliberate_source_tree_on_pythonpath_is_left_alone(tmp_path: Path) -> None:
    """Running from a checkout you put on PYTHONPATH yourself must keep working.

    That is the one case where the injected entry *is* our own location, and
    reordering it would be us overriding a deliberate choice.
    """

    _, ours = _build_shadowed_layout(tmp_path)
    result = _run(
        """
import sys
sys.path.insert(0, {ours!r})
import alicebot_api, probe_dependency
print("CORRECT_BUILD", getattr(probe_dependency, "CORRECT_BUILD", False))
print("version", alicebot_api.__version__)
""",
        pythonpath=str(ours),
        ours=ours,
        foreign=tmp_path / "unused",
    )

    assert result.returncode == 0, result.stderr
    assert "CORRECT_BUILD True" in result.stdout


def test_no_pythonpath_leaves_sys_path_untouched(tmp_path: Path) -> None:
    _, ours = _build_shadowed_layout(tmp_path)
    environment = dict(os.environ)
    environment.pop("PYTHONPATH", None)

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            textwrap.dedent(
                """
                import sys
                sys.path.insert(0, {ours!r})
                before = list(sys.path)
                import alicebot_api
                print("UNCHANGED", before == sys.path)
                """
            ).format(ours=str(ours)),
        ],
        capture_output=True,
        text=True,
        env=environment,
        timeout=60,
    )

    assert result.returncode == 0, result.stderr
    assert "UNCHANGED True" in result.stdout


@pytest.mark.parametrize("relative_form", ("./our-site-packages", "our-site-packages"))
def test_relative_sys_path_entries_are_still_matched(tmp_path: Path, relative_form: str) -> None:
    """The first draft of this fix compared an absolute path against a relative
    ``sys.path`` entry, so the lookup missed and the reorder never happened."""

    foreign, ours = _build_shadowed_layout(tmp_path)
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(foreign)

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            textwrap.dedent(
                """
                import os, sys
                foreign = os.path.abspath({foreign!r})
                index = next(
                    position for position, entry in enumerate(sys.path)
                    if os.path.abspath(entry) == foreign
                )
                sys.path.insert(index + 1, {relative!r})
                import alicebot_api
                import probe_dependency
                print("CORRECT_BUILD", getattr(probe_dependency, "CORRECT_BUILD", False))
                """
            ).format(foreign=str(foreign), relative=relative_form),
        ],
        capture_output=True,
        text=True,
        env=environment,
        cwd=tmp_path,
        timeout=60,
    )

    assert result.returncode == 0, f"relative entry not matched:\n{result.stderr}"
    assert "CORRECT_BUILD True" in result.stdout
