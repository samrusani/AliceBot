"""AliceBot foundation API package."""

from importlib.metadata import PackageNotFoundError, version as _distribution_version

try:
    __version__ = _distribution_version("alice-memory")
except PackageNotFoundError:  # running from a source tree without an install
    __version__ = "0.0.0+source"

__all__ = ["__version__"]
