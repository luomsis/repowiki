"""Validator tests: every rule with a positive and a negative fixture."""

from __future__ import annotations

import copy

import pytest
from conftest import valid_page
from repowiki.validate import (
    check_knowledge_card,
    check_knowledge_module,
    check_knowledge_plan,
    check_overview,
    check_page,
    extract_refs,
)


class TestPageRules:
    def test_valid_page_passes(self, repo):
        res = check_page(valid_page(), "项目概述", repo)
        assert res.ok, res.errors

    def test_missing_h1_fails(self, repo):
        text = valid_page().replace("# 项目概述\n", "", 1)
        res = check_page(text, "项目概述", repo)
        assert not res.ok and any("一级标题" in e for e in res.errors)

    def test_wrong_h1_autofixed(self, repo):
        text = valid_page().replace("# 项目概述", "# 错误标题", 1)
        res = check_page(text, "项目概述", repo)
        assert res.ok
        assert res.text.startswith("# 项目概述")
        assert any("H1" in f for f in res.fixed)

    def test_missing_section_fails(self, repo):
        text = valid_page().replace("## 核心组件", "## 其他组件", 1)
        res = check_page(text, "项目概述", repo)
        assert not res.ok and any("核心组件" in e for e in res.errors)

    def test_performance_heading_variant_ok(self, repo):
        text = valid_page().replace("## 性能与一致性考量", "## 性能考量")
        res = check_page(text, "项目概述", repo)
        assert res.ok

    def test_truncated_page_fails(self, repo):
        res = check_page("# 项目概述\n\n<cite>\n- [README.md](file://README.md)\n</cite>\n", "项目概述", repo)
        assert not res.ok

    def test_missing_cite_fails(self, repo):
        text = valid_page()
        start = text.index("<cite>")
        end = text.index("</cite>") + len("</cite>")
        res = check_page(text[:start] + text[end:], "项目概述", repo)
        assert not res.ok and any("cite" in e for e in res.errors)

    def test_dangling_file_ref_fails(self, repo):
        text = valid_page().replace("file://README.md", "file://nope/README.md")
        res = check_page(text, "项目概述", repo)
        assert not res.ok and any("不存在" in e for e in res.errors)

    def test_line_range_clamped(self, repo):
        text = valid_page().replace(
            "[README.md:1-2](file://README.md#L1-L2)", "[README.md:1-9999](file://README.md#L1-L9999)"
        )
        res = check_page(text, "项目概述", repo)
        assert res.ok
        assert any("钳制" in f for f in res.fixed)
        # README.md is 3 lines in the fixture; the out-of-range 9999 gets clamped
        assert "README.md:1-3" in res.text

    def test_backslash_path_normalized(self, repo):
        text = valid_page().replace("file://src/demo/main.py", "file://src\\demo\\main.py")
        res = check_page(text, "项目概述", repo)
        assert "file://src/demo/main.py" in res.text

    def test_unbalanced_mermaid_fails(self, repo):
        # remove one closing fence -> odd number of fences
        text = valid_page().replace('A["api.py"] --> B["models.py"]\n```\n', 'A["api.py"] --> B["models.py"]\n')
        res = check_page(text, "项目概述", repo)
        assert not res.ok and any("围栏" in e for e in res.errors)

    def test_too_few_mermaid_fails(self, repo):
        text = valid_page()
        for opener in ("```mermaid\nsequenceDiagram", "```mermaid\ngraph LR"):
            i = text.index(opener)
            j = text.index("```", i + len(opener)) + 3
            text = text[:i] + text[j:]
        res = check_page(text, "项目概述", repo)
        assert not res.ok and any("mermaid" in e for e in res.errors)

    def test_toc_anchor_autofixed(self, repo):
        text = valid_page().replace("9. [结论](#结论)", "9. [结论](#jielun)")
        res = check_page(text, "项目概述", repo)
        assert res.ok
        assert "[结论](#结论)" in res.text
        assert any("目录" in f for f in res.fixed)

    def test_leftover_placeholder_fails(self, repo):
        text = valid_page().replace("## 简介", "## 简介\n{{SOMETHING}}")
        res = check_page(text, "项目概述", repo)
        assert not res.ok and any("占位符" in e for e in res.errors)

    def test_placeholder_inside_code_passes(self, repo):
        # a page documenting the placeholder mechanism itself: literals
        # inside fenced blocks / inline code are legitimate content
        text = valid_page().replace(
            "## 简介",
            "## 简介\n\n用 `{{TITLE}}` 表示标题占位符：\n\n```text\nrender(\"{{TITLE}}\")\n```\n",
            1,
        )
        res = check_page(text, "项目概述", repo)
        assert res.ok, res.errors

    def test_wiki_to_wiki_link_warns(self, repo):
        text = valid_page().replace(
            "demo 是一个微型示例服务。", "见 [其他页](../快速开始.md)。"
        )
        res = check_page(text, "项目概述", repo)
        assert res.ok and any("页间链接" in w for w in res.warnings)

    def test_update_page_requires_update_summary(self, repo):
        res = check_page(valid_page(), "项目概述", repo, is_update=True)
        assert not res.ok and any("更新摘要" in e for e in res.errors)

    def test_extract_refs(self):
        refs = extract_refs("- [a](file://a.py#L1-L10) and [b](file://b.py)")
        assert refs == [("a.py", 1, 10), ("b.py", None, None)]


class TestKnowledgePlan:
    def _known(self):
        return {"src/demo/config.py", "src/demo/log.py", "src/demo/errors.py", "pyproject.toml"}

    def _plan(self):
        return {
            "modules": [
                {"id": "m01", "title": "核心模块", "scope": ["src/demo/"], "children": [], "depends_on": [], "related_to": []}
            ],
            "cards": [
                {"id": "k01", "title": "配置系统", "category": "configuration_system",
                 "scope": ["**"], "source_files": ["src/demo/config.py"]}
            ],
        }

    def test_valid(self):
        errors, _ = check_knowledge_plan(self._plan(), self._known())
        assert errors == []

    def test_bad_category(self):
        p = self._plan()
        p["cards"][0]["category"] = "misc"
        errors, _ = check_knowledge_plan(p, self._known())
        assert any("category 非法" in e for e in errors)

    def test_dangling_reference(self):
        p = self._plan()
        p["cards"][0]["source_files"] = ["no/such.py"]
        errors, _ = check_knowledge_plan(p, self._known())
        assert any("不存在" in e for e in errors)

    def test_dangling_child_ref(self):
        p = self._plan()
        p["modules"][0]["children"] = ["m99"]
        errors, _ = check_knowledge_plan(p, self._known())
        assert any("m99" in e for e in errors)

    def test_duplicate_ids(self):
        p = self._plan()
        p["modules"].append(copy.deepcopy(p["modules"][0]))
        errors, _ = check_knowledge_plan(p, self._known())
        assert any("重复" in e for e in errors)


class TestKnowledgeCard:
    def _card(self):
        return (
            "---\n"
            "kind: configuration_system\n"
            "name: 配置系统\n"
            "category: configuration_system\n"
            "scope:\n  - '**'\n"
            "source_files:\n  - src/demo/config.py\n"
            "---\n\n"
            "# 配置系统\n\n"
            "## 1. 体系概览\n内容\n\n"
            "## 2. 关键文件与包\n内容\n\n"
            "## 3. 架构与设计约定\n内容\n\n"
            "## 4. 开发者应遵循的规则\n内容\n"
        )

    def test_valid(self, repo):
        res = check_knowledge_card(self._card(), "配置系统", "configuration_system", repo)
        assert res.ok, res.errors

    def test_missing_section(self, repo):
        card = self._card().replace("## 4. 开发者应遵循的规则", "## 4. 别的")
        res = check_knowledge_card(card, "配置系统", "configuration_system", repo)
        assert not res.ok

    def test_missing_front_matter(self, repo):
        res = check_knowledge_card("# x\n", "配置系统", "configuration_system", repo)
        assert not res.ok and any("front matter" in e for e in res.errors)

    def test_bad_h1(self, repo):
        card = self._card().replace("# 配置系统", "# 另一个标题")
        res = check_knowledge_card(card, "配置系统", "configuration_system", repo)
        assert not res.ok and any("H1" in e for e in res.errors)


class TestKnowledgeModule:
    def test_valid(self, tmp_path):
        d = tmp_path / "模块"
        d.mkdir()
        for n in ("概述.md", "技术栈.md", "架构设计.md"):
            (d / n).write_text("内容\n")
        assert check_knowledge_module(d).ok

    def test_missing_required(self, tmp_path):
        d = tmp_path / "模块"
        d.mkdir()
        (d / "概述.md").write_text("内容\n")
        res = check_knowledge_module(d)
        assert not res.ok and any("技术栈" in e for e in res.errors)


class TestOverview:
    def test_valid(self):
        text = (
            "# demo Wiki 总览\n\n"
            "介绍。\n\n"
            "## 章节导航\n- 项目概述\n\n"
            "## 如何使用本 Wiki\n先看概述。\n"
        )
        res = check_overview(text, "demo")
        assert res.ok, res.errors

    def test_h1_autofixed(self):
        text = "# 总览\n\n## 章节导航\nx\n\n## 如何使用本 Wiki\ny\n"
        res = check_overview(text, "demo")
        assert res.ok and "# demo Wiki 总览" in res.text
