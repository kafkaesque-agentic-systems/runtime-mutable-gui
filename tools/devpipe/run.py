"""Launcher: `python3 run.py <command>` runs the devpipe CLI from this folder.

The installed `devpipe` wrapper and the vendored copy in `tools/devpipe/` both
start here, so the toolkit needs no installation step of its own.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from devpipe.cli import main  # noqa: E402  (the path line above must run first)

if __name__ == "__main__":
    sys.exit(main())
