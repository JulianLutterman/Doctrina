
try:
    from importlib.metadata import version, PackageNotFoundError
except ImportError:
    from importlib_metadata import version, PackageNotFoundError

__title__ = "tinker"
try:
    __version__ = version(__title__)
except PackageNotFoundError:
    __version__ = "0.0.0"  # Fallback for vendored usage
