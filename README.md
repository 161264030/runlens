# RunLens

RunLens 是 Linux 程序执行取证工具：记录运行证据、比较 good/bad runs，定位有意义的行为分叉。

**当前版本：M1。已实现命令运行、主进程 /proc 资源采样、JSON 存储和运行查看。**

目标开发环境：Ubuntu 22.04，Python 3.10+。运行时仅使用标准库。

## 安装

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
runlens --help
runlens doctor
runlens doctor --json
```

`doctor --json` 中的 `--json` 是实际参数，不要输入方括号。
Doctor 检查 Linux、strace、readelf 和 /proc 的可访问性；不执行外部工具或检测 ptrace 权限。
如需安装外部工具：`sudo apt install strace binutils`。
M1 的运行和资源采样不依赖 strace/readelf；它们供后续阶段使用。
Windows/macOS 可安装、查看帮助、检查环境和读取已有记录，运行采集需要 Linux。

## 运行示例

在项目根目录中执行：

```sh
runlens run -- python3 tests/fixtures/programs/sleep.py
runlens run -- python3 tests/fixtures/programs/exit1.py
runlens list
runlens list --json
```

第二条目标程序返回 1，所以 RunLens 也返回 1；记录仍会保存。这是正常的失败运行记录。
将输出中的实际 `run_...` ID 复制到 inspect 命令，例如在 shell 变量中保存它：

```sh
RUN_ID=run_替换成实际的32位ID
runlens inspect "$RUN_ID"
runlens inspect --json "$RUN_ID"
```

默认存储目录是**调用时当前目录**下的 `.runlens/runs/`。每次运行创建：

```text
.runlens/runs/run_<uuid>/
  metadata.json
  resources.jsonl
```

metadata 保存 argv、cwd、PID、UTC 时间、monotonic 纳秒时间、耗时、退出结果、
资源峰值和采集状态。resources.jsonl 每行是一次资源采样。
目录已加入 .gitignore。目标程序的 stdin/stdout/stderr 直接继承，摘要写到 stderr。
不保存程序输出，不记录环境变量。

## 自定义采样和路径

```sh
runlens run --interval 0.01 --runs-dir ./my-runs --cwd /tmp -- /bin/sleep 0.3
runlens list --runs-dir ./my-runs
```

所有 RunLens 的 run 选项必须写在目标命令之前；目标命令后面的参数原样传递。
`--` 用来标记 RunLens 参数结束。`--interval` 单位是秒，默认 0.02，必须为有限正数。
`--cwd` 仅改变目标进程的工作目录，不改变存储目录的解析位置。
跨目录查看记录时，使用相同的绝对 `--runs-dir` 路径。

## 退出状态和采集范围

- 正常结束：传递目标程序退出码，包括非零退出码。
- 因信号终止：保存原始负 returncode 和明确的信号名；CLI 返回 128+信号编号。
  SIGTERM 对应 143。
- 启动失败：返回 127，保存 launch_failed 和错误消息。
- 参数错误或未实现的 diff：返回 2；存储/采集错误返回 1。
- 捕获到 Ctrl+C：标记 interrupted，回收直接子进程并返回 130。

采集器读取 `/proc/<pid>/status`、`fd`、`stat`，记录 RSS、RSS 高水位、线程数、
FD 数和用户/内核 CPU ticks。RSS 峰值包含观察到的 VmHWM；线程和 FD 峰值是采样最大值。
仅观察直接启动的主进程，不聚合其子进程。不同文件的读取不是原子快照。

采集状态：`sampled` 表示获得数据且未观察到读取错误；`partial` 表示部分读取失败或采集中断；
`unavailable` 表示未得到核心资源测量值。缺失测量用 null 表示，错误记录在 samples/metadata 中。
短进程可能在首次采样前退出。sampled 不表示捕获到了所有瞬时峰值。
POSIX 上新运行目录权限为 0700，数据文件为 0600。

磁盘故障会明确报告错误，但不保证最终 metadata 能写入。SIGKILL、系统崩溃或断电可能留下
running 状态的未完成记录；M1 尚未自动恢复这类记录。中断后的清理只负责直接子进程。

## 测试与 CI

```sh
python -m pip install -e ".[dev]" -c constraints-dev.txt
ruff check .
ruff format --check .
mypy
pytest
pytest tests/integration/test_runner.py -q
```

GitHub Actions 在 Ubuntu 22.04 的 Python 3.10 和 3.12 上执行所有检查。
集成测试包含 exit0、exit1、sleep、memory_growth、thread_spawn、fd_open 和信号退出。
非 Linux 环境会跳过真实 /proc 测试。远程 CI 状态须在推送后确认。

`runlens --debug inspect <run-id>` 可查看 CLI 错误 traceback。
M2 将引入 strace 事件采集；M3 引入 capsule；M4 实现 diff。当前尚无这些功能。
更多设计见 docs/architecture.md、docs/schema.md 和 docs/decisions/。
