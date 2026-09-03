"""repowiki: deterministic repo-wiki build system driven by coding agents.

The tool itself contains no LLM and makes no network calls. It plans tasks,
validates agent-produced output, and assembles metadata; intelligence is
supplied by whatever agent drives the worker loop:

    loop: task = repowiki next --claim --json
          if empty and busy > 0: wait and retry   # others are mid-flight
          if empty and busy == 0: exit            # all done
          execute the task spec (read source, write output)
          repowiki check --task <id> --json       # auto-fix + status flip
"""

from importlib.metadata import PackageNotFoundError, version as _package_version

try:
    __version__ = _package_version("repowiki")
except PackageNotFoundError:  # running from an uninstalled source tree
    __version__ = "0.0.0"
