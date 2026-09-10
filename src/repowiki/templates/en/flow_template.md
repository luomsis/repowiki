# {{TITLE}}

## Contents
1. [Introduction](#introduction)
2. [Flow Overview](#flow-overview)
3. [Key Steps](#key-steps)
4. [Involved Components](#involved-components)
5. [Data and State Changes](#data-and-state-changes)
6. [Troubleshooting Guide](#troubleshooting-guide)
7. [Conclusion](#conclusion)

## Introduction
<One paragraph: what this flow is, what triggers it, where it ends, and where it lives in the repository.>

## Flow Overview
<One paragraph sketching the end-to-end path (entry → key stages → exit), with a sequence diagram.>

```mermaid
sequenceDiagram
participant Trigger as "Trigger"
participant Step1 as "Stage 1<br/>file.py"
participant Step2 as "Stage 2<br/>file.py"
Trigger->>Step1 : "start"
Step1->>Step2 : "process"
Step2-->>Step1 : "result"
Step1-->>Trigger : "done"
```

Diagram sources
- [<path>:<from>-<to>](file://<path>#L<from>-L<to>)

Section sources
- [<path>:<from>-<to>](file://<path>#L<from>-L<to>)

## Key Steps
### Step 1: <name>
- Input: <what enters this step>
- Handling: <what happens, key code path>
- Failure path: <how failures surface and are handled>

Section sources
- [<path>:<from>-<to>](file://<path>#L<from>-L<to>)

### Step 2: <name>
- ...

**Section sources**
- [<path>:<from>-<to>](file://<path>#L<from>-L<to>)

## Involved Components
- <component/module>: its role in this flow (bullet list, in call order).

Section sources
- [<path>:<from>-<to>](file://<path>#L<from>-L<to>)

## Data and State Changes
<Before/after comparison of data and state: inputs/outputs, side effects, state-machine transitions; use a flow diagram when transitions are involved.>

```mermaid
graph LR
A["State A"] -->|"event"| B["State B"]
B -->|"done"| C["Final"]
```

Diagram sources
- [<path>:<from>-<to>](file://<path>#L<from>-L<to>)

Section sources
- [<path>:<from>-<to>](file://<path>#L<from>-L<to>)

## Troubleshooting Guide
- <common failure → cause → how to locate → relevant code location.>

Section sources
- [<path>:<from>-<to>](file://<path>#L<from>-L<to>)

## Conclusion
<One paragraph: when this flow applies, correct usage, and caveats.>

Section sources
- [<path>:<from>-<to>](file://<path>#L<from>-L<to>)

<cite>
**Files referenced**
- [<file name>](file://<repo-relative path>)
- [<file name>](file://<repo-relative path>)
</cite>
