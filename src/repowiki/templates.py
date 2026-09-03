"""Template asset loader.

Templates are plain text files under ``repowiki/templates/<locale>/`` rendered
with ``{{PLACEHOLDER}}`` substitution. Unknown placeholders are left intact on
purpose so the validator can flag forgotten substitutions in agent output.
Each locale ships a full template set; the task specs themselves carry the
output-language instructions.
"""

from __future__ import annotations

import re
from pathlib import Path

from .i18n import DEFAULT_LOCALE

TEMPLATE_DIR = Path(__file__).parent / "templates"

_PLACEHOLDER_RE = re.compile(r"\{\{([A-Z][A-Z0-9_]*)\}\}")


def load(name: str, locale: str = DEFAULT_LOCALE) -> str:
    path = TEMPLATE_DIR / locale / name
    if not path.is_file():  # fall back to the default locale's set
        path = TEMPLATE_DIR / DEFAULT_LOCALE / name
    return path.read_text(encoding="utf-8")


def render(text: str, **kwargs) -> str:
    def sub(m: re.Match) -> str:
        key = m.group(1)
        return str(kwargs[key]) if key in kwargs else m.group(0)

    return _PLACEHOLDER_RE.sub(sub, text)


def render_file(name: str, locale: str = DEFAULT_LOCALE, **kwargs) -> str:
    return render(load(name, locale), **kwargs)


def placeholders(text: str) -> list[str]:
    return sorted(set(_PLACEHOLDER_RE.findall(text)))
