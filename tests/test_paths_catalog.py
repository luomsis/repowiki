"""Paths (sanitize/anchor) and catalog schema tests."""

from __future__ import annotations

import unicodedata

import pytest

from conftest import valid_catalog

from repowiki.catalog import flatten, validate_catalog, catalog_tree_text
from repowiki.paths import github_anchor, sanitize_component, unique_name


class TestSanitize:
    def test_nfc_normalization(self):
        nfd = unicodedata.normalize("NFD", "项目概述")
        assert sanitize_component(nfd) == "项目概述"

    def test_illegal_chars_replaced(self):
        assert "/" not in sanitize_component("a/b")
        assert sanitize_component("a:b") == "a：b"

    def test_control_chars_stripped(self):
        assert sanitize_component("a\x00b\x1fc") == "abc"

    def test_empty_fallback(self):
        assert sanitize_component("") == "untitled"
        assert sanitize_component(" . ") == "untitled"

    def test_unique_suffix(self):
        used = {"名"}
        assert unique_name("名", used) == "名__2"
        assert unique_name("名", used) == "名__3"


class TestAnchor:
    def test_chinese_colon_stripped(self):
        assert github_anchor("附录：一键运行清单") == "附录一键运行清单"

    def test_mixed_case_and_space(self):
        assert github_anchor("BM25 关键词搜索算法") == "bm25-关键词搜索算法"

    def test_punctuation_removed(self):
        assert github_anchor("Hello, World!") == "hello-world"


class TestCatalogValidate:
    def _known(self):
        return {"README.md", "src/demo/main.py", "src/demo/models.py", "src/demo/api.py",
                "pyproject.toml", "src/demo/config.py", "src/demo/utils.py"}

    def test_valid(self):
        errors, _ = validate_catalog(valid_catalog(), self._known())
        assert errors == []

    def test_bad_json_type(self):
        errors, _ = validate_catalog([], self._known())
        assert errors

    def test_duplicate_title(self):
        c = valid_catalog()
        c["chapters"][1]["title"] = "项目概述"
        errors, _ = validate_catalog(c, self._known())
        assert any("title 重复" in e for e in errors)

    def test_bad_slug(self):
        c = valid_catalog()
        c["chapters"][0]["slug"] = "Bad Slug!"
        errors, _ = validate_catalog(c, self._known())
        assert any("slug 非法" in e for e in errors)

    def test_page_with_children(self):
        c = valid_catalog()
        c["chapters"][0]["children"][0]["children"] = [c["chapters"][0]["children"][0]]
        errors, _ = validate_catalog(c, self._known())
        assert any("不能有 children" in e for e in errors)

    def test_depth_exceeded(self):
        c = valid_catalog()
        node = c["chapters"][0]
        node["kind"] = "chapter"
        child = dict(node, id="c0101x", title="一级子章")
        child["children"] = [dict(child, id="c010101x", title="二级子章", children=[
            dict(child, id="c0101011x", title="三级子章", children=[
                dict(child, id="c01010111x", title="四级子章")
            ])
        ])]
        c["chapters"][0] = child
        errors, _ = validate_catalog(c, self._known())
        assert any("深度" in e for e in errors)

    def test_unknown_dependent_file_dropped_with_warning(self):
        c = valid_catalog()
        c["chapters"][0]["dependent_files"] = ["README.md", "no/such/file.py"]
        errors, warnings = validate_catalog(c, self._known())
        assert errors == []
        assert any("no/such/file.py" in w for w in warnings)
        assert c["chapters"][0]["dependent_files"] == ["README.md"]


class TestFlatten:
    def test_paths_derived(self):
        nodes = flatten(valid_catalog())
        by_id = {n.id: n for n in nodes}
        assert by_id["c01"].output == "zh/content/项目概述/项目概述.md"
        assert by_id["c0101"].output == "zh/content/项目概述/核心概念.md"
        assert by_id["c02"].output == "zh/content/快速开始.md"
        assert by_id["c0101"].parent_id == "c01"

    def test_collision_suffix(self):
        c = valid_catalog()
        c["chapters"][1]["title"] = "核心概念"
        nodes = flatten(c)
        outs = [n.output for n in nodes]
        assert len(outs) == len(set(outs))

    def test_chapter_path(self):
        nodes = flatten(valid_catalog())
        by_id = {n.id: n for n in nodes}
        assert by_id["c0101"].chapter_path(by_id) == "项目概述 > 核心概念"

    def test_tree_text_contains_briefs(self):
        text = catalog_tree_text(flatten(valid_catalog()))
        assert "项目概述" in text and "page_brief" not in text
