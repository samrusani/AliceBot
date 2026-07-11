"""Setuptools build hook for runtime resources stored outside the package tree.

The repository keeps Alembic migrations and public eval fixtures in their
natural contributor-facing locations. Wheels still need private copies so the
advertised CLI works when invoked outside a source checkout.
"""

from __future__ import annotations

from pathlib import Path
import shutil

from setuptools import setup
from setuptools.command.build_py import build_py as _build_py


ROOT = Path(__file__).resolve().parent


class BuildPyWithRuntimeResources(_build_py):
    def run(self) -> None:
        super().run()
        resource_root = Path(self.build_lib) / "alicebot_api" / "_resources"
        resource_root.mkdir(parents=True, exist_ok=True)
        (resource_root / "eval").mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / "apps" / "api" / "alembic.ini", resource_root / "alembic.ini")
        shutil.copy2(
            ROOT / "eval" / "fixtures" / "public_eval_suites.json",
            resource_root / "eval" / "public_eval_suites.json",
        )
        shutil.copytree(
            ROOT / "apps" / "api" / "alembic",
            resource_root / "alembic",
            dirs_exist_ok=True,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"),
        )


setup(cmdclass={"build_py": BuildPyWithRuntimeResources})
