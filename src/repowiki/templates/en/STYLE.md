# Style & Diagram Rules (every page must follow)

## Language
- Write plain English; keep code identifiers, class names, file paths, and config keys verbatim.
- Objective, factual tone — no marketing language. No emoji. No tables (unless a config listing truly needs one).

## Section Sources & Diagram Sources (citation format, mandatory)
- Every body section ends with a "Section sources" list; every mermaid diagram is followed by a "Diagram sources" list.
- Link format (paths relative to the repo root, forward slashes, line ranges must not exceed the file's real length):
  - `[README.md:1-120](file://README.md#L1-L120)`
  - `src/graphiti/graphiti.py:146-283` → `[graphiti/graphiti.py:146-283](file://graphiti/graphiti.py#L146-L283)`
- Whole-file references may use the shorter form `[nodes.py](file://graphiti_core/nodes.py)` (inside the `<cite>` block).
- Referenced files must really exist in the repository; never link other wiki pages (zero page-to-page links).
- If a section has no corresponding code, write: `[This section is conceptual; no specific files are analyzed, hence no "Section sources"]`

## Mermaid diagram style
- Structure diagrams use `graph TB`, dependency/relationship diagrams `graph LR`, interaction flows `sequenceDiagram`, type relationships `classDiagram`.
- Node labels must be wrapped in double quotes; wrap long labels with `<br/>` and keep the key identifier visible:

```mermaid
graph TB
subgraph "Application layer"
REST["REST service<br/>FastAPI"]
WEB["Web UI<br/>Next.js"]
end
subgraph "Core library"
CORE["Core engine<br/>engine.py"]
end
REST --> CORE
WEB --> REST
```

- sequenceDiagram participants and messages are quoted too:

```mermaid
sequenceDiagram
participant Client as "Client"
participant API as "API layer"
participant Core as "Core engine"
Client->>API : "POST /api/xxx"
API->>Core : "invoke core method"
Core-->>API : "structured result"
API-->>Client : "JSON response"
```

## Other page conventions
- Exactly one H1 heading, equal to the page title; body levels start at `##`, sub-components use `###`.
- The "Contents" section is a numbered list whose anchors follow GitHub-style anchors (lowercase, punctuation dropped, spaces → `-`, e.g. `Quick Start Guide` → `#quick-start-guide`).
- The Conclusion section states the topic's one-sentence positioning and usage advice.
