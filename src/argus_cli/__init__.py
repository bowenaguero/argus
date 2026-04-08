from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("argus")
except PackageNotFoundError:
    __version__ = "unknown"
