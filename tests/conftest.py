"""Shared fixtures: a small synthetic repo and valid catalog/page samples."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from repowiki.paths import WikiPaths

FILES: dict[str, str] = {
    "README.md": "# demo\nA tiny demo service.\n",
    "pyproject.toml": "[project]\nname = 'demo'\n",
    "src/demo/__init__.py": "",
    "src/demo/main.py": "def main():\n    '''entry'''\n    from demo.api import serve\n    serve()\n\n\nif __name__ == '__main__':\n    main()\n",
    "src/demo/models.py": (
        "from dataclasses import dataclass\n\n\n"
        "@dataclass\nclass Item:\n    id: int\n    name: str\n"
    ),
    "src/demo/api.py": (
        "from demo.models import Item\n\n"
        "ITEMS = []\n\n\n"
        "def serve():\n    print('serving')\n\n\n"
        "def add(item: Item):\n    ITEMS.append(item)\n"
    ),
    "src/demo/config.py": "import os\n\nDEBUG = os.environ.get('DEBUG', '0') == '1'\n",
    "src/demo/utils.py": "def slugify(s: str) -> str:\n    return s.lower().replace(' ', '-')\n",
    "src/demo/log.py": "import logging\n\nlog = logging.getLogger('demo')\n",
    "src/demo/errors.py": "class NotFound(Exception):\n    pass\n",
    "tests/test_main.py": "def test_main():\n    assert True\n",
    "tests/test_api.py": "def test_add():\n    assert True\n",
    "scripts/build.sh": "#!/bin/sh\necho build\n",
}


def make_repo(tmp_path: Path, git: bool = False) -> Path:
    repo = tmp_path / "demo-repo"
    for rel, content in FILES.items():
        f = repo / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(content, encoding="utf-8")
    if git:
        run = lambda *a: subprocess.run(
            a, cwd=str(repo), check=True, capture_output=True
        )
        run("git", "init", "-q")
        run("git", "config", "user.email", "t@t")
        run("git", "config", "user.name", "t")
        run("git", "add", "-A")
        run("git", "commit", "-qm", "init")
    return repo


@pytest.fixture
def repo(tmp_path):
    return make_repo(tmp_path, git=False)


@pytest.fixture
def git_repo(tmp_path):
    return make_repo(tmp_path, git=True)


@pytest.fixture
def paths(repo):
    p = WikiPaths(repo)
    return p


def valid_catalog() -> dict:
    return {
        "repo_name": "demo",
        "chapters": [
            {
                "id": "c01", "title": "项目概述", "slug": "project-overview",
                "summary": "概述", "kind": "chapter",
                "dependent_files": ["README.md", "pyproject.toml"],
                "page_brief": "项目定位、模块划分、快速上手",
                "children": [
                    {
                        "id": "c0101", "title": "核心概念", "slug": "core-concepts",
                        "summary": "概念", "kind": "page",
                        "dependent_files": ["src/demo/models.py", "src/demo/api.py"],
                        "page_brief": "Item 模型与 API 的关系",
                    },
                ],
            },
            {
                "id": "c02", "title": "快速开始", "slug": "quick-start",
                "summary": "开始", "kind": "page",
                "dependent_files": ["src/demo/main.py", "README.md"],
                "page_brief": "如何安装与运行 demo",
            },
        ],
    }


def valid_page(title: str = "项目概述") -> str:
    return f"""# {title}

<cite>
**本文引用的文件**
- [README.md](file://README.md)
- [src/demo/main.py](file://src/demo/main.py)
</cite>

## 目录
1. [简介](#简介)
2. [项目结构](#项目结构)
3. [核心组件](#核心组件)
4. [架构总览](#架构总览)
5. [详细组件分析](#详细组件分析)
6. [依赖关系分析](#依赖关系分析)
7. [性能与一致性考量](#性能与一致性考量)
8. [故障排查指南](#故障排查指南)
9. [结论](#结论)

## 简介
demo 是一个微型示例服务。

## 项目结构
- src/demo：核心包
- tests：测试

```mermaid
graph TB
A["入口<br/>main.py"] --> B["API<br/>api.py"]
```

图表来源
- [src/demo/main.py:1-7](file://src/demo/main.py#L1-L7)

章节来源
- [README.md:1-2](file://README.md#L1-L2)

## 核心组件
- main：入口

章节来源
- [src/demo/main.py:1-7](file://src/demo/main.py#L1-L7)

## 架构总览
调用链简单。

```mermaid
sequenceDiagram
participant U as "用户"
participant A as "API"
U->>A : "请求"
A-->>U : "响应"
```

图表来源
- [src/demo/api.py:1-8](file://src/demo/api.py#L1-L8)

## 详细组件分析
### 入口
- 职责：启动

章节来源
- [src/demo/main.py:1-7](file://src/demo/main.py#L1-L7)

## 依赖关系分析
- api 依赖 models

```mermaid
graph LR
A["api.py"] --> B["models.py"]
```

图表来源
- [src/demo/api.py:1-8](file://src/demo/api.py#L1-L8)

## 性能与一致性考量
- 单进程内存列表，无并发保障

章节来源
- [src/demo/api.py:1-8](file://src/demo/api.py#L1-L8)

## 故障排查指南
- 启动失败：检查依赖

章节来源
- [src/demo/main.py:1-7](file://src/demo/main.py#L1-L7)

## 结论
demo 用于演示 repowiki 流程。

章节来源
- [README.md:1-2](file://README.md#L1-L2)
"""


def write_catalog(paths: WikiPaths, catalog: dict | None = None) -> None:
    paths.state_dir.mkdir(parents=True, exist_ok=True)
    paths.catalog_file.write_text(
        json.dumps(catalog or valid_catalog(), ensure_ascii=False), encoding="utf-8"
    )
