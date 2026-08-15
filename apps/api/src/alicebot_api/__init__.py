"""AliceBot foundation API package."""

from importlib.metadata import PackageNotFoundError, version as _distribution_version
import os
import sys


def _prefer_own_runtime_on_sys_path() -> None:
    """Put our own installation ahead of anything ``PYTHONPATH`` injected.

    ``uvx`` and ``pipx`` install Alice into an isolated environment, but Python
    still honours ``PYTHONPATH`` from the parent process and places those
    entries near the front of ``sys.path``. A host that launches Alice from
    inside a conda environment or a virtualenv therefore leaks its own
    site-packages into our interpreter, and a dependency built for a different
    Python ABI shadows the one we installed.

    Reported from a real Hermes install on 2026-08-15: a Python 3.11 NumPy
    extension being loaded by Alice's own Python runtime, which kills
    ``alice-memory mcp`` on startup with an ABI error. The user's workaround
    was to unset ``PYTHONPATH``, ``VIRTUAL_ENV`` and ``CONDA_PREFIX`` before
    launching. Nobody should have to know that.

    This runs in ``__init__`` deliberately, because ``onramp`` imports
    ``sqlite_store`` at module scope and that imports NumPy, so by the time any
    ``main()`` is called the damage is done.

    **We reorder, never remove.** Anything ``PYTHONPATH`` provides that we do
    not ship still resolves exactly as before; only a shadowing copy of a
    dependency we ship ourselves loses. Running from a source tree with
    ``PYTHONPATH`` pointing at that tree is left alone, because then the
    injected entry *is* our own location.
    """

    raw_python_path = os.environ.get("PYTHONPATH")
    if not raw_python_path:
        return

    def _canonical(entry: str) -> str:
        # sys.path and PYTHONPATH may both carry relative entries, and the
        # interpreter resolves them against the working directory. Compare
        # everything in one absolute form or the lookups below silently miss.
        return os.path.normcase(os.path.abspath(entry))

    injected = {_canonical(entry) for entry in raw_python_path.split(os.pathsep) if entry}
    if not injected:
        return

    # The directory holding this package, i.e. the site-packages we were
    # installed into.
    own_location = _canonical(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if own_location in injected:
        # Someone is deliberately running us from a tree on PYTHONPATH. Theirs.
        return

    normalized_path = [_canonical(entry) for entry in sys.path]
    try:
        own_index = normalized_path.index(own_location)
    except ValueError:
        return

    first_injected_index = next(
        (index for index, entry in enumerate(normalized_path) if entry in injected),
        None,
    )
    if first_injected_index is None or own_index < first_injected_index:
        return  # already ahead of the injected entries

    sys.path.insert(first_injected_index, sys.path.pop(own_index))


_prefer_own_runtime_on_sys_path()

try:
    __version__ = _distribution_version("alice-memory")
except PackageNotFoundError:  # running from a source tree without an install
    __version__ = "0.0.0+source"

__all__ = ["__version__"]
