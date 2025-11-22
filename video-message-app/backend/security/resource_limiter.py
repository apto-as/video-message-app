"""
Resource Limiter - リソース枯渇攻撃対策
並列処理制限、タイムアウト、メモリ監視
"""

import asyncio
import logging
import psutil
import time
from asyncio import Semaphore, TimeoutError as AsyncTimeoutError
from contextlib import asynccontextmanager
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class ResourceMetrics:
    """リソース使用状況メトリクス"""
    active_tasks: int = 0
    total_tasks_executed: int = 0
    total_tasks_failed: int = 0
    total_tasks_timeout: int = 0
    average_execution_time: float = 0.0
    max_execution_time: float = 0.0
    current_memory_mb: float = 0.0
    peak_memory_mb: float = 0.0
    cpu_percent: float = 0.0
    last_updated: datetime = field(default_factory=datetime.now)


class ResourceLimiter:
    """
    リソース制限管理クラス
    並列処理数、タイムアウト、メモリ使用量を制限
    """

    def __init__(
        self,
        max_concurrent: int = 5,
        default_timeout: float = 30.0,
        max_memory_mb: float = 500.0,
        max_cpu_percent: float = 80.0,
        name: str = "default"
    ):
        """
        Args:
            max_concurrent: 最大並列処理数
            default_timeout: デフォルトタイムアウト（秒）
            max_memory_mb: 最大メモリ使用量（MB）
            max_cpu_percent: 最大CPU使用率（%）
            name: リミッター名（識別用）
        """
        self.max_concurrent = max_concurrent
        self.default_timeout = default_timeout
        self.max_memory_mb = max_memory_mb
        self.max_cpu_percent = max_cpu_percent
        self.name = name

        # セマフォ（並列処理制限）
        self.semaphore = Semaphore(max_concurrent)

        # メトリクス
        self.metrics = ResourceMetrics()

        # 実行時間記録
        self._execution_times = []
        self._max_execution_history = 100

        # プロセス監視用
        self.process = psutil.Process()

        logger.info(
            f"ResourceLimiter '{name}' initialized: "
            f"max_concurrent={max_concurrent}, timeout={default_timeout}s, "
            f"max_memory={max_memory_mb}MB, max_cpu={max_cpu_percent}%"
        )

    @asynccontextmanager
    async def acquire(self, timeout: Optional[float] = None):
        """
        リソース取得（コンテキストマネージャー）

        Args:
            timeout: タイムアウト（秒、Noneの場合はdefault_timeout使用）

        Raises:
            asyncio.TimeoutError: タイムアウト発生
            MemoryError: メモリ不足
            RuntimeError: CPU使用率超過

        Example:
            async with limiter.acquire():
                # 保護された処理
                result = await expensive_operation()
        """
        if timeout is None:
            timeout = self.default_timeout

        # リソースチェック
        await self._check_resources()

        # セマフォ取得（タイムアウト付き）
        try:
            await asyncio.wait_for(self.semaphore.acquire(), timeout=timeout)
        except AsyncTimeoutError:
            self.metrics.total_tasks_timeout += 1
            logger.warning(f"ResourceLimiter '{self.name}': セマフォ取得タイムアウト（{timeout}秒）")
            raise asyncio.TimeoutError(
                f"リソース取得がタイムアウトしました（待機時間: {timeout}秒）。"
                "現在のサーバー負荷が高いため、しばらく時間をおいてから再度お試しください。"
            )

        self.metrics.active_tasks += 1
        start_time = time.perf_counter()

        try:
            yield
            # 成功時の処理
            execution_time = time.perf_counter() - start_time
            self._record_execution_time(execution_time)
            self.metrics.total_tasks_executed += 1
            logger.debug(f"ResourceLimiter '{self.name}': タスク完了（{execution_time:.2f}秒）")

        except Exception as e:
            # エラー時の処理
            self.metrics.total_tasks_failed += 1
            logger.error(f"ResourceLimiter '{self.name}': タスク失敗 - {str(e)}")
            raise

        finally:
            # 必ずセマフォを解放
            self.semaphore.release()
            self.metrics.active_tasks -= 1
            self.metrics.last_updated = datetime.now()

    async def _check_resources(self):
        """
        リソース使用状況チェック
        メモリ、CPU使用率を確認し、超過していればエラー
        """
        # メモリチェック
        memory_info = self.process.memory_info()
        memory_mb = memory_info.rss / 1024 / 1024
        self.metrics.current_memory_mb = memory_mb

        if memory_mb > self.metrics.peak_memory_mb:
            self.metrics.peak_memory_mb = memory_mb

        if memory_mb > self.max_memory_mb:
            logger.error(
                f"ResourceLimiter '{self.name}': メモリ使用量超過 "
                f"({memory_mb:.2f}MB > {self.max_memory_mb}MB)"
            )
            raise MemoryError(
                f"メモリ使用量が制限を超えました（{memory_mb:.2f}MB / {self.max_memory_mb}MB）。"
                "システム負荷が高いため、処理を実行できません。"
            )

        # CPUチェック
        cpu_percent = self.process.cpu_percent(interval=0.1)
        self.metrics.cpu_percent = cpu_percent

        if cpu_percent > self.max_cpu_percent:
            logger.warning(
                f"ResourceLimiter '{self.name}': CPU使用率が高い "
                f"({cpu_percent:.1f}% > {self.max_cpu_percent}%)"
            )
            # CPUの場合は警告のみ（エラーにはしない）
            # raise RuntimeError(
            #     f"CPU使用率が制限を超えました（{cpu_percent:.1f}% / {self.max_cpu_percent}%）"
            # )

    def _record_execution_time(self, execution_time: float):
        """実行時間を記録し、統計を更新"""
        self._execution_times.append(execution_time)

        # 履歴サイズ制限
        if len(self._execution_times) > self._max_execution_history:
            self._execution_times.pop(0)

        # 統計更新
        self.metrics.average_execution_time = sum(self._execution_times) / len(self._execution_times)
        self.metrics.max_execution_time = max(self._execution_times)

    def get_available_slots(self) -> int:
        """利用可能なスロット数を取得"""
        return self.max_concurrent - self.metrics.active_tasks

    def get_metrics(self) -> Dict[str, Any]:
        """現在のメトリクスを取得"""
        return {
            "name": self.name,
            "max_concurrent": self.max_concurrent,
            "active_tasks": self.metrics.active_tasks,
            "available_slots": self.get_available_slots(),
            "total_executed": self.metrics.total_tasks_executed,
            "total_failed": self.metrics.total_tasks_failed,
            "total_timeout": self.metrics.total_tasks_timeout,
            "average_execution_time": round(self.metrics.average_execution_time, 2),
            "max_execution_time": round(self.metrics.max_execution_time, 2),
            "current_memory_mb": round(self.metrics.current_memory_mb, 2),
            "peak_memory_mb": round(self.metrics.peak_memory_mb, 2),
            "cpu_percent": round(self.metrics.cpu_percent, 1),
            "last_updated": self.metrics.last_updated.isoformat()
        }

    def reset_metrics(self):
        """メトリクスをリセット"""
        self.metrics = ResourceMetrics()
        self._execution_times = []
        logger.info(f"ResourceLimiter '{self.name}': メトリクスをリセットしました")

    async def execute_with_timeout(self, coro, timeout: Optional[float] = None):
        """
        タイムアウト付きでコルーチンを実行

        Args:
            coro: 実行するコルーチン
            timeout: タイムアウト（秒）

        Returns:
            コルーチンの実行結果

        Raises:
            asyncio.TimeoutError: タイムアウト発生
        """
        if timeout is None:
            timeout = self.default_timeout

        try:
            async with self.acquire(timeout=timeout):
                result = await asyncio.wait_for(coro, timeout=timeout)
                return result
        except AsyncTimeoutError:
            self.metrics.total_tasks_timeout += 1
            logger.error(f"ResourceLimiter '{self.name}': 処理タイムアウト（{timeout}秒）")
            raise asyncio.TimeoutError(
                f"処理がタイムアウトしました（制限時間: {timeout}秒）。"
                "処理に時間がかかりすぎています。"
            )

    def is_available(self) -> bool:
        """リソースが利用可能かチェック"""
        return self.get_available_slots() > 0

    def get_queue_position(self) -> int:
        """現在の待機位置を取得（概算）"""
        return max(0, self.metrics.active_tasks - self.max_concurrent)

    async def wait_for_availability(self, timeout: float = 60.0) -> bool:
        """
        リソースが利用可能になるまで待機

        Args:
            timeout: 最大待機時間（秒）

        Returns:
            利用可能になったらTrue、タイムアウトしたらFalse
        """
        start_time = time.perf_counter()

        while time.perf_counter() - start_time < timeout:
            if self.is_available():
                return True
            await asyncio.sleep(0.5)

        logger.warning(f"ResourceLimiter '{self.name}': 待機タイムアウト（{timeout}秒）")
        return False


# === グローバルリミッターインスタンス ===

# 音声クローン用リミッター（重い処理）
voice_clone_limiter = ResourceLimiter(
    max_concurrent=3,  # 3並列まで
    default_timeout=60.0,  # 60秒タイムアウト
    max_memory_mb=500.0,  # 500MB制限
    max_cpu_percent=80.0,
    name="voice_clone"
)

# 音声合成用リミッター（中程度の処理）
voice_synthesis_limiter = ResourceLimiter(
    max_concurrent=5,  # 5並列まで
    default_timeout=30.0,  # 30秒タイムアウト
    max_memory_mb=300.0,  # 300MB制限
    max_cpu_percent=70.0,
    name="voice_synthesis"
)

# Prosody調整用リミッター（軽い処理）
prosody_adjustment_limiter = ResourceLimiter(
    max_concurrent=10,  # 10並列まで
    default_timeout=15.0,  # 15秒タイムアウト
    max_memory_mb=200.0,  # 200MB制限
    max_cpu_percent=60.0,
    name="prosody_adjustment"
)


def get_all_limiters() -> Dict[str, ResourceLimiter]:
    """すべてのリミッターを取得"""
    return {
        "voice_clone": voice_clone_limiter,
        "voice_synthesis": voice_synthesis_limiter,
        "prosody_adjustment": prosody_adjustment_limiter
    }


def get_system_metrics() -> Dict[str, Any]:
    """システム全体のメトリクスを取得"""
    process = psutil.Process()
    memory_info = process.memory_info()

    return {
        "process_id": process.pid,
        "memory_mb": round(memory_info.rss / 1024 / 1024, 2),
        "cpu_percent": process.cpu_percent(interval=0.1),
        "num_threads": process.num_threads(),
        "limiters": {
            name: limiter.get_metrics()
            for name, limiter in get_all_limiters().items()
        }
    }
