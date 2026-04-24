# 下一步工作计划：收尾当前功能迭代

## Context

当前工作区有 7 个已修改文件 + 3 个未跟踪文件，涵盖功能线：
- 抠图处理器质量参数 + 预缩放 + 遮罩合成
- 配置路径解析修复
- 任务创建幂等键
- 健康检查 Redis/Worker 独立状态
- 前端任务提交幂等键 + 会话恢复
- 项目服务管理脚本

## 步骤

### 1. 先跑一次现有测试确认破裂点

```bash
cd /home/huangnianzhi/tools && PYTHONPATH=backend python -m pytest backend/tests/ -v -k "not integration"
```

预期 `test_cutout_processor.py` 需要更新（`_ensure_rgba_png_bytes` 已改为 `_to_mask`，`process()` 增加了 validate 调用）。

### 2. 修复并增强 `backend/tests/test_cutout_processor.py`

- 元数据测试：增加 `params_schema` 中 quality 参数的断言（default="balanced"，options=["fast","balanced","high"]）
- validate 测试：增加合法值（fast/balanced/high/{}）和非法值（extreme/空串）的测试
- process 测试：params 加上 `quality` 参数
- 新增测试：大图预缩放验证（1000x800 → 推理尺寸 ≤768，输出尺寸仍为 1000x800）
- 新增测试：quality=fast 对应 max_size=512
- 集成测试：params 补上 `quality: "balanced"`

### 3. 合并 `test_config_paths.py` 到 `test_config.py`

RULER.md 规定测试文件与实现文件一一对应，两个文件都测试 `config.py` 的 `Settings` 类。将 `test_config_paths.py` 中的两个测试移到 `test_config.py`，删除 `test_config_paths.py`。

### 4. 审查 `test_api_tasks_idempotency.py`

使用 Fake 对象模拟 Redis/TaskStore，结构良好。可选补一个"幂等键对应的 task 被删后清理脏键"的边界测试。

### 5. 运行全量测试

```bash
cd /home/huangnianzhi/tools && PYTHONPATH=backend python -m pytest backend/tests/ -v -k "not integration"
```

确保全部通过。

### 6. 分 5 组提交

| # | 类型 | 描述 | 文件 |
|---|------|------|------|
| 1 | fix | 修复配置路径解析，相对路径基于项目根目录解析 | config.py, test_config.py |
| 2 | feat | 抠图处理器增加质量参数、预缩放和遮罩合成 | cutout.py, test_cutout_processor.py |
| 3 | feat | 任务创建增加幂等键支持，避免重复提交 | api/tasks.py, test_api_tasks_idempotency.py |
| 4 | feat | 健康检查增加 Redis 和 Worker 独立状态 | main.py, test_main.py |
| 5 | feat | 前端增加任务提交幂等键与会话恢复 | api/index.js, ToolWorkbench.vue |
| 6 | chore | 添加项目服务管理脚本 | scripts/project_service.sh |

### 7. 最后验证

```bash
git status  # 确认无遗漏
git log --oneline -6  # 确认提交清晰
```
