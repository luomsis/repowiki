# 仓库协作规则（AGENTS.md）

## 发版规则（每次发布新版本必须遵守）

1. **同步升版本号**：`pyproject.toml` 与 `.claude-plugin/plugin.json` 保持一致。
2. **更新双语 CHANGELOG**：`CHANGELOG.md` 与 `CHANGELOG.en.md` 各加一节，按「新增 / 修复 / 文档 / 测试 / 清理」分类。
3. **打包 wheel**：`python -m build --wheel`（或 `pip wheel --no-deps -w dist/ .`），产物在 `dist/repowiki-<版本>-py3-none-any.whl`。
4. **whl 附到 GitHub Release**：`gh release create` 时作为 asset 上传（或事后 `gh release upload`）——README「离线安装」一节直接引用 Release 页附带的 `repowiki-*.whl`，缺了会破坏离线安装路径。
5. **测试门禁**：发版前 `pytest` 全绿。
6. push main 后用 `gh release create vX.Y.Z --target <HEAD sha>` 创建正式 Release 并回报 URL。
7. **PyPI 发布**：Release 发布后 `.github/workflows/pypi.yml` 通过 Trusted Publisher 自动上传 sdist+wheel（OIDC 免 token）；首次上传前需在 PyPI 预登记 Pending Publisher（https://pypi.org/manage/account/publishing/ ：Owner `luomsis` · Repo `repowiki` · Workflow `pypi.yml` · Environment `pypi`），之后新版本无需任何 PyPI 侧操作。
