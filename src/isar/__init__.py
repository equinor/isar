from importlib.metadata import PackageNotFoundError, distribution

try:
    __version__ = distribution(__name__).version
except PackageNotFoundError:
    pass  # package is not installed
