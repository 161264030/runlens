# RunLens

RunLens 是 Linux 程序执行取证工具：记录运行证据、比较 good/bad runs，定位有意义的行为分叉。

**状态：M0 已实现；采集与分析功能尚未实现。**

## Quick Start

需要 Python 3.10+。推荐 Ubuntu 24.04+ 或 WSL2；Windows/macOS 可安装并查看帮助和环境检查。

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
runlens --help
runlens doctor
runlens doctor --json
```

Windows PowerShell 激活命令：`.\.venv\Scripts\Activate.ps1`。
不激活也可直接使用 `.\.venv\Scripts\python.exe -m runlens --help`。

Ubuntu 缺少工具时安装：`sudo apt install strace binutils`。
doctor 检查 Linux、PATH 上的 strace/readelf 和可访问的 /proc；检查过程只读，
不执行被检测工具、不请求 root。它不验证 ptrace 权限或工具版本兼容性。

## 命令状态

| 命令 | 当前行为 |
| --- | --- |
| `runlens doctor [--json]` | 输出环境检查结果，全部通过返回 0，否则返回 1 |
| `runlens run -- ./prog` | M1 占位，返回 2，不执行程序 |
| `runlens list` | M1 占位，返回 2 |
| `runlens inspect <run-id>` | M1 占位，返回 2 |
| `runlens diff <good> <bad>` | M4 占位，返回 2 |

每个子命令均支持 `--help`。`runlens --version` 显示当前版本。
用法错误返回 2。`python -m runlens` 与安装后的入口等价。

## 开发与验收

```sh
python -m pip install -e ".[dev]" -c constraints-dev.txt
ruff check .
ruff format --check .
mypy
pytest
```

开发依赖及其传递依赖均固定版本；运行时不依赖第三方包。
GitHub Actions 在 Ubuntu 的 Python 3.10/3.12/3.14 上安装包，运行 lint、格式、
类型、测试和 CLI 检查。远程 CI 状态须在推送至 GitHub 后确认。

架构见 docs/architecture.md，诊断格式见 docs/schema.md，下一步见 docs/backlog.md。
M0 不包含 strace 采集、运行存储、C++、capsule 或 diff 分析。
