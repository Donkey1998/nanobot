# 定时任务模块

> **文件位置**: [nanobot/cron/](../../../nanobot/cron/)
> **主要文件**: service.py (347 行), types.py
> **最后更新**: 2026-02-10

---

## 1. 概述

定时任务模块（Cron Service）提供任务调度和执行功能，支持 cron 表达式和间隔调度。

### 核心职责

- **任务调度**: 根据时间表触发任务
- **持久化**: 保存任务到磁盘
- **结果投递**: 将任务结果发送到指定渠道
- **生命周期管理**: 启用、禁用、删除任务

### 支持的调度类型

| 类型 | 说明 | 示例 |
|------|------|------|
| **cron** | 标准 cron 表达式 | `"0 9 * * *"` (每天 9 点) |
| **every** | 固定间隔（秒） | `{"every": 60}` (每 60 秒) |
| **at** | 一次性定时任务 | `{"at": "2026-02-10T10:00:00Z"}` |

### 相关模块

- [工具系统](tools-system.md) - cron 工具的实现

---

## 2. 设计理念

### 2.1 异步调度

使用 asyncio 实现非阻塞的调度循环，与其他组件并发运行。

### 2.2 单次调度触发

调度器计算最近的下次运行时间，只调度一次触发器，避免定时器漂移。

### 2.3 任务持久化

任务保存到 JSON 文件（`~/.nanobot/cron.json`），重启后自动恢复。

---

## 3. 核心机制

### 3.1 调度循环

```
CronService.start()
    ├─ 加载任务存储
    ├─ 计算下次运行时间
    └─ 启动定时器
    ↓
定时器等待
    ↓
时间到达 → _on_timer()
    ├─ 查找到期任务
    ├─ 执行任务
    │   ├─ 调用 on_job 回调
    │   └─ 更新任务状态
    ├─ 重新计算下次运行时间
    └─ 重新启动定时器
```

### 3.2 Cron 表达式解析

使用 [croniter](https://github.com/kiorky/croniter) 库解析标准 cron 表达式。

**格式**: `分 时 日 月 周`

**示例**:
```python
"0 9 * * *"      # 每天 9:00
"30 */2 * * *"   # 每 2 小时的 30 分
"0 0 * * 0"      # 每周日 0:00
"0 0 1 * *"      # 每月 1 号 0:00
```

### 3.3 任务数据结构

**代码位置**: [types.py](../../../nanobot/cron/types.py)

```python
@dataclass
class CronJob:
    id: str                              # 唯一标识符
    name: str                            # 任务名称
    enabled: bool                        # 是否启用
    schedule: CronSchedule               # 调度配置
    payload: CronPayload                 # 任务内容
    state: CronJobState                  # 运行状态
    created_at_ms: int                   # 创建时间
    updated_at_ms: int                   # 更新时间
    delete_after_run: bool = False       # 运行后删除（一次性任务）
```

---

## 4. 关键接口

### 4.1 CronService

#### 构造函数

```python
def __init__(
    self,
    store_path: Path,
    on_job: Callable[[CronJob], Coroutine[Any, Any, str | None]] = None
):
    self.store_path = store_path  # 任务存储路径
    self.on_job = on_job  # 任务执行回调
```

#### 方法

```python
async def start(self) -> None:
    """启动 Cron 服务"""

def stop(self) -> None:
    """停止 Cron 服务"""

def list_jobs(self, include_disabled: bool = False) -> list[CronJob]:
    """列出所有任务"""

def add_job(
    self,
    name: str,
    schedule: CronSchedule,
    message: str,
    deliver: bool = False,
    channel: str | None = None,
    to: str | None = None,
    delete_after_run: bool = False,
) -> CronJob:
    """添加新任务"""

def remove_job(self, job_id: str) -> bool:
    """按 ID 移除任务"""

def enable_job(self, job_id: str, enabled: bool = True) -> CronJob | None:
    """启用或禁用任务"""

async def run_job(self, job_id: str, force: bool = False) -> bool:
    """手动运行任务"""

def status(self) -> dict:
    """获取服务状态"""
```

---

## 5. 使用示例

### 5.1 创建和启动服务

```python
import asyncio
from pathlib import Path
from nanobot.cron.service import CronService

async def job_callback(job):
    """任务执行回调"""
    print(f"执行任务: {job.name}")
    print(f"消息: {job.payload.message}")
    # 这里可以将消息发送到 Agent 处理
    return f"任务 {job.name} 已完成"

async def main():
    # 创建服务
    service = CronService(
        store_path=Path.home() / ".nanobot" / "cron.json",
        on_job=job_callback
    )

    # 启动服务
    await service.start()

    # 服务会持续运行...
    await asyncio.sleep(3600)

asyncio.run(main())
```

### 5.2 添加定时任务

```python
from nanobot.cron.types import CronSchedule

# 添加每天 9 点执行的任务
job = service.add_job(
    name="morning_greeting",
    schedule=CronSchedule(
        kind="cron",
        expr="0 9 * * *"
    ),
    message="早上好！今天有什么计划？",
    deliver=True,
    channel="telegram",
    to="123456"
)

print(f"任务已添加: {job.id}")
```

### 5.3 添加间隔任务

```python
# 添加每 5 分钟执行的任务
job = service.add_job(
    name="status_check",
    schedule=CronSchedule(
        kind="every",
        every_ms=300000  # 5 分钟 = 300000 毫秒
    ),
    message="检查系统状态",
    deliver=False  # 不发送到渠道
)
```

### 5.4 添加一次性任务

```python
from datetime import datetime, timedelta

# 添加 1 小时后执行的一次性任务
target_time = datetime.now() + timedelta(hours=1)

job = service.add_job(
    name="reminder",
    schedule=CronSchedule(
        kind="at",
        at_ms=int(target_time.timestamp() * 1000)
    ),
    message="别忘了参加会议！",
    deliver=True,
    channel="telegram",
    to="123456",
    delete_after_run=True  # 执行后自动删除
)
```

### 5.5 列出和管理任务

```python
# 列出所有启用的任务
jobs = service.list_jobs(include_disabled=False)

for job in jobs:
    print(f"任务: {job.name}")
    print(f"  下次运行: {job.state.next_run_at_ms}")
    print(f"  状态: {job.state.last_status}")

# 禁用任务
service.enable_job(job.id, enabled=False)

# 手动运行任务
await service.run_job(job.id, force=True)

# 删除任务
service.remove_job(job.id)
```

---

## 6. 扩展指南

### 6.1 添加任务超时控制

```python
class TimeoutCronService(CronService):
    async def _execute_job(self, job):
        """带超时的任务执行"""
        timeout = 60  # 60 秒超时

        try:
            result = await asyncio.wait_for(
                self.on_job(job),
                timeout=timeout
            )
            job.state.last_status = "ok"
            job.state.last_error = None
        except asyncio.TimeoutError:
            job.state.last_status = "error"
            job.state.last_error = f"任务超时（{timeout}秒）"
```

### 6.2 添加任务重试

```python
class RetryingCronService(CronService):
    async def _execute_job(self, job, max_retries=3):
        """支持重试的任务执行"""
        for attempt in range(max_retries):
            try:
                result = await self.on_job(job)
                job.state.last_status = "ok"
                break
            except Exception as e:
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # 指数退避
                    continue
                job.state.last_status = "error"
                job.state.last_error = str(e)
```

### 6.3 添加任务依赖

```python
class DependentCronService(CronService):
    def add_job(self, name, schedule, depends_on=None, **kwargs):
        """支持任务依赖"""
        job = super().add_job(name, schedule, **kwargs)
        if depends_on:
            job.metadata["depends_on"] = depends_on
        return job

    async def _on_timer(self):
        """处理任务依赖"""
        # 等待依赖任务完成
        for job in self._store.jobs:
            if job.enabled and job.metadata.get("depends_on"):
                dependency = self._get_job(job.metadata["depends_on"])
                if dependency and dependency.state.last_status != "ok":
                    continue  # 跳过此任务
                # 执行任务
                await self._execute_job(job)
```

### 6.4 添加任务历史记录

```python
class HistoricalCronService(CronService):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._history_path = kwargs.get("history_path")

    async def _execute_job(self, job):
        """记录任务执行历史"""
        start_time = time.time()

        # 执行任务
        result = await self.on_job(job)

        # 记录历史
        duration = time.time() - start_time
        history_entry = {
            "job_id": job.id,
            "job_name": job.name,
            "executed_at": datetime.now().isoformat(),
            "duration": duration,
            "status": job.state.last_status,
            "result": result
        }

        # 保存到历史文件
        with open(self._history_path, "a") as f:
            f.write(json.dumps(history_entry) + "\n")
```

### 6.5 添加任务通知

```python
class NotifyingCronService(CronService):
    async def _execute_job(self, job):
        """支持任务失败通知"""
        result = await self.on_job(job)

        # 如果任务失败，发送通知
        if job.state.last_status == "error":
            await self._send_notification(
                title=f"任务 {job.name} 失败",
                message=job.state.last_error,
                channel="alert"
            )

        return result

    async def _send_notification(self, title, message, channel):
        # 实现通知逻辑（发送到 Alert 系统）
        pass
```

---

## 相关文件和目录

### 主要源代码

- [nanobot/cron/service.py](../../../nanobot/cron/service.py) - Cron 服务（347 行）
- [nanobot/cron/types.py](../../../nanobot/cron/types.py) - 任务数据模型

### 依赖模块

- [nanobot/agent/tools/cron.py](../../../nanobot/agent/tools/cron.py) - Cron 工具

### 相关文档

- [工具系统模块文档](tools-system.md)

## 外部依赖

- **croniter**: [https://github.com/kiorky/croniter](https://github.com/kiorky/croniter) - Cron 表达式解析

## 数据存储

```
~/.nanobot/
└── cron.json  # 任务持久化存储
```
