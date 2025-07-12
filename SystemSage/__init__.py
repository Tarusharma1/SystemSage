"""SystemSage - A powerful cross-platform system management and monitoring tool."""
import sys
from .server import mcp, serve

if sys.version_info >= (3, 8):
    from importlib import metadata
else:
    # Python < 3.8
    import importlib_metadata as metadata

try:
    __version__ = metadata.version("systemsage")
except metadata.PackageNotFoundError:
    # Package is not installed
    __version__ = "0.0.0-dev"


__all__ = ["mcp", "serve"]

def main():
    """Entry point for the CLI."""
    serve()

if __name__ == "__main__":
    main()