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

__version__ = "0.1.0"
