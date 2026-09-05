# Windows 原生支持：stdlib 双文件锁后端

**中文** | [English](../../en/adr/0001-windows-native-support.md)

v0.2.0 及之前 Windows 是明确 Non-Goal（README/SKILL.md 声明"请在 WSL 中使用"），因为并发状态控制依赖
POSIX `fcntl.flock`。用户要求原生支持后，我们选择按平台选择 stdlib 锁后端——POSIX 保持 `fcntl`，
Windows 用 `msvcrt.locking`（约 20 行，零新增依赖），语义同样是"单机阻塞独占锁"，与工具的单机部署模型一致。

## Considered Options

- **portalocker 第三方库**：API 统一，但打破"唯一依赖 pyyaml"的极简定位，离线安装文档也要跟着加物料；
- **用原子 mkdir 重造锁、彻底去掉文件锁**：单一代码路径，但要改动并发核心（事务互斥与 stale 回收推导全部重来），风险与测试成本最高；
- **维持 WSL-only**：不满足需求。

## Consequences

- Windows CI（`windows-latest`）纳入矩阵成为回归兜底；本机开发仍只需 macOS/Linux。
- `msvcrt.locking(LK_LOCK)` 约 10 秒抢不到锁会抛错（`fcntl` 是无限阻塞），已映射为带重试提示的 `StateError`，
  是两个后端唯一的语义差异。
- 文档中的 bash 惯例（`nohup … &`、`command -v`）在 SKILL.md 里补充了 PowerShell 等价写法。
