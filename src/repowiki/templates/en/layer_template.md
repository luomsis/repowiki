# {{TITLE}}

## Contents
1. [Introduction](#introduction)
2. [Layer Overview](#layer-overview)
3. [Layer Responsibilities](#layer-responsibilities)
4. [Layer Dependencies and Call Rules](#layer-dependencies-and-call-rules)
5. [Vertical Slice: One Call Through the Layers](#vertical-slice-one-call-through-the-layers)
6. [Cross-Cutting Concerns](#cross-cutting-concerns)
7. [Troubleshooting Guide](#troubleshooting-guide)
8. [Conclusion](#conclusion)

## Introduction
<One paragraph: what this layered architecture is, the principle behind the layering, and where it lives in the repository.>

## Layer Overview
<One paragraph sketching how many layers there are and each layer's one-line role, with a vertically stacked layer diagram (top layer on top, representative components per layer).>

```mermaid
graph TB
subgraph "Interface layer"
ENTRY["Entry dispatch<br/>main.py"]
end
subgraph "Business layer"
SVC["Business logic<br/>service.py"]
end
subgraph "Data layer"
REPO["Data access<br/>repo.py"]
end
ENTRY --> SVC
SVC --> REPO
```

Diagram sources
- [<path>:<from>-<to>](file://<path>#L<from>-L<to>)

Section sources
- [<path>:<from>-<to>](file://<path>#L<from>-L<to>)

## Layer Responsibilities
### <Layer 1>
- Responsibility: <what this layer does>
- Representative modules: <key files/classes>
- Must not do: <layer violations, e.g. bypassing the business layer to touch the data layer>

Section sources
- [<path>:<from>-<to>](file://<path>#L<from>-L<to>)

### <Layer 2>
- ...

Section sources
- [<path>:<from>-<to>](file://<path>#L<from>-L<to>)

## Layer Dependencies and Call Rules
<One paragraph: who may call whom, which dependency directions are forbidden, and how violations surface. With a dependency-direction diagram.>

```mermaid
graph LR
UI["Interface layer"] -->|"may call"| BIZ["Business layer"]
BIZ -->|"may call"| DATA["Data layer"]
DATA -.->|"reverse dependency forbidden"| UI
```

Diagram sources
- [<path>:<from>-<to>](file://<path>#L<from>-L<to>)

Section sources
- [<path>:<from>-<to>](file://<path>#L<from>-L<to>)

## Vertical Slice: One Call Through the Layers
<Pick one representative call path and show with a sequence diagram how it crosses from the interface layer down to the data layer and back.>

```mermaid
sequenceDiagram
participant E as "Interface layer"
participant B as "Business layer"
participant D as "Data layer"
E->>B : "invoke business method"
B->>D : "read/write data"
D-->>B : "return result"
B-->>E : "assemble response"
```

Diagram sources
- [<path>:<from>-<to>](file://<path>#L<from>-L<to>)

Section sources
- [<path>:<from>-<to>](file://<path>#L<from>-L<to>)

## Cross-Cutting Concerns
First a short prose paragraph on where cross-cutting mechanisms land overall, then bullets: mechanism → which layers → key code locations.

Section sources
- [<path>:<from>-<to>](file://<path>#L<from>-L<to>)

## Troubleshooting Guide
- <common error/symptom → cause → how to locate → relevant code location (e.g. how to trace a suspected layer violation).>

Section sources
- [<path>:<from>-<to>](file://<path>#L<from>-L<to>)

## Conclusion
<One paragraph: the layering rationale, correct usage, and caveats.>

Section sources
- [<path>:<from>-<to>](file://<path>#L<from>-L<to>)

<cite>
**Files referenced**
- [<file name>](file://<repo-relative path>)
- [<file name>](file://<repo-relative path>)
</cite>
