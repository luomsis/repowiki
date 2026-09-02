"""Template asset loader.

Templates are plain text files under ``repowiki/templates/`` rendered with
``{{PLACEHOLDER}}`` substitution. Unknown placeholders are left intact on
purpose so the validator can flag forgotten substitutions in agent output.
"""

from __future__ import annotations

import re
from pathlib import Path

TEMPLATE_DIR = Path(__file__).parent / "templates"

_PLACEHOLDER_RE = re.compile(r"\{\{([A-Z][A-Z0-9_]*)\}\}")


def load(name: str) -> str:
    path = TEMPLATE_DIR / name
    text = path.read_text(encoding="utf-8")
    return text


def render(text: str, **kwargs) -> str:
    def sub(m: re.Match) -> str:
        key = m.group(1)
        return str(kwargs[key]) if key in kwargs else m.group(0)

    return _PLACEHOLDER_RE.sub(sub, text)


def render_file(name: str, **kwargs) -> str:
    return render(load(name), **kwargs)


def placeholders(text: str) -> list[str]:
    return sorted(set(_PLACEHOLDER_RE.findall(text)))
