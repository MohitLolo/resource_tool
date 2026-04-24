# Celery Worker 无声崩溃问题修复方案

## 问题现象

- Worker 启动成功（日志出现 `celery@ubuntu ready.`）
- 有任务进入 Redis 队列后，worker 进程无声退出
- 日志没有任何异常栈、退出码或信号记录
- 任务持续 pendding，前端卡住
- 当前用 `-P solo` 模式启动的 worker 正常工作

## 根因分析

最可能的根因：**缺省 `prefork` 池 + C 扩展（OpenCV/ONNX/rembg）在 fork 后不兼容导致子进程崩溃**。

Python 的多线程 + fork 存在已知问题：
1. 主进程加载了 OpenCV/ONNX 等持有 C 级别线程锁的库
2. fork 后子进程可能处于死锁或悬挂状态
3. 子进程可能收到 SIGSEGV/SIGABRT，这些信号不会被 Python `try/except` 或 `logging` 捕获
4. `prefork` 池所有子进程都崩溃后，主进程退出

当前用 `-P solo`（单进程、不 fork）能正常工作印证了此推断。

## 方案

### 选项 A：改默认池为 `solo`（推荐，短期立即可用）

修改 `start_celery_worker.sh`，默认使用 `solo` 池：

```bash
# 改动一行
exec celery -A app.tasks.worker worker --loglevel="${LOGLEVEL}" -P solo "$@"
```

**优点：**
- 一行改动，立即解决
- C 扩展兼容性好（不 fork）

**缺点：**
- 无并行处理能力（一次只处理一个任务）
- solo 池没有子进程隔离，某个任务崩溃会导致整个 worker 退出
- 不适合生产环境多任务并发

---

### 选项 B：`solo` 池 + 进程级守护（推荐，最终方案）

在选项 A 基础上增加：

1. **启动包装脚本**：捕捉退出码和信号
2. **自动重启**：退出后立即拉起
3. **崩溃日志**：用 `trap` 捕获 SIGSEGV/SIGABRT 并记录

修改 `start_celery_worker.sh`：

```bash
#!/usr/bin/env bash
set -euo pipefail

# ... 前置检查不变 ...

MAX_RESTARTS=5
RESTART_DELAY=2
restart_count=0

while true; do
  echo "[worker] starting (attempt $((restart_count + 1)))..."
  celery -A app.tasks.worker worker --loglevel="${LOGLEVEL}" -P solo "$@"
  exit_code=$?
  
  if [ $exit_code -eq 0 ]; then
    echo "[worker] exited normally"
    exit 0
  fi
  
  restart_count=$((restart_count + 1))
  if [ $restart_count -ge $MAX_RESTARTS ]; then
    echo "[worker] too many restarts ($restart_count), giving up" >&2
    exit 1
  fi
  
  echo "[worker] crashed with exit code $exit_code, restarting in ${RESTART_DELAY}s..."
  sleep $RESTART_DELAY
done
```

**覆盖的信号和退出码：**
| 退出码/信号 | 含义 | 处理 |
|---|---|---|
| 0 | 正常退出 | 不重启 |
| 非 0 | 异常退出 | 重启，≤5 次 |
| SIGSEGV(11) | 段错误 | 被 bash + trap 捕获 |
| SIGABRT(6) | 异常终止 | 被 bash + trap 捕获 |

---

### 选项 C：`prefork` 池 + fork 安全（长期优化）

如果未来需要并行处理能力：

1. 延迟加载 C 扩展库到任务函数中，而不是模块级别导入
2. 设置 `CELERYD_FORK_SLEEP_TIMEOUT` 或使用 `--executor=gevent`
3. 或用 `--pool=threads`（GIL 问题但无 fork 问题）

**开发环境推荐选项 B，生产环境再考虑选项 C。**

## 实施步骤

### Step 1：修改启动脚本

文件：`backend/scripts/start_celery_worker.sh`

- 移除 `exec`，改为循环重启包装
- 默认加 `-P solo`
- 增加重启次数限制（最多 5 次）
- 增加 `trap` 捕获信号并记录

### Step 2：测试重启行为

```bash
# 手动验证：启动 worker，观察日志
bash backend/scripts/start_celery_worker.sh --loglevel=debug

# 在新终端提交任务，确认正常处理
curl -X POST http://localhost:8000/api/tasks \
  -F "input_file=@some_image.png" \
  -F "processor=image.cutout"
```

### Step 3：验证健康检查联动

确认 `/api/health` 能正确反映 worker 状态：
- worker running → `worker: ok`
- worker 重启间隙 → `worker: down`，`status: degraded`

### Step 4：写日志到专属文件

修改 `scripts/project_service.sh` 中 worker 的日志路径，确保：
- stdout 和 stderr 都写到 `/tmp/gameasset/worker.log`
- Celery 的 `--logfile` 参数也指向同一个文件（可选）

## 验证方式

1. **启动测试**：`bash backend/scripts/start_celery_worker.sh` → 输出 `[worker] starting` + Celery banner
2. **处理任务**：提交一个 cutout 或 watermark 任务 → 状态从 pending → processing → completed
3. **崩溃恢复**：`kill -KILL <worker_pid>` → 日志输出 `crashed with exit code` → 自动重启
4. **超限停止**：连续 crash 6 次 → 输出 `too many restarts` → 不再重启
5. **正常退出**：`kill <worker_pid>` → SIGTERM → celery 正常退出 → exit 0 → 不重启
