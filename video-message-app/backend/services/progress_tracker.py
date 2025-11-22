"""
Real-time Progress Tracking System for Video Pipeline

Supports:
- WebSocket connections for real-time updates
- SSE (Server-Sent Events) as fallback
- In-memory storage with automatic cleanup
- Multi-subscriber support (one task, many clients)
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, Set, Optional, AsyncIterator
from enum import Enum
import asyncio
import json
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# Progress Event Types
# ============================================================================

class EventType(str, Enum):
    """Progress event types"""
    STAGE_UPDATE = "stage_update"
    PROGRESS_UPDATE = "progress_update"
    ERROR = "error"
    COMPLETE = "complete"
    HEARTBEAT = "heartbeat"


@dataclass
class ProgressEvent:
    """Progress event structure"""
    task_id: str
    event_type: EventType
    data: Dict
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps({
            "task_id": self.task_id,
            "event_type": self.event_type.value,
            "data": self.data,
            "timestamp": self.timestamp.isoformat()
        })

    def to_sse(self) -> str:
        """Convert to SSE format"""
        return f"data: {self.to_json()}\n\n"


# ============================================================================
# Progress Tracker Service
# ============================================================================

class ProgressTracker:
    """
    Central progress tracking service with pub-sub pattern

    Features:
    - Multi-subscriber support: Multiple clients can subscribe to same task
    - Automatic cleanup: Old progress data removed after retention period
    - Heartbeat: Periodic keepalive messages to detect disconnections
    - Thread-safe: Async-safe operations with locks
    """

    def __init__(self, retention_minutes: int = 60):
        # Progress data storage: task_id -> List[ProgressEvent]
        self._progress_history: Dict[str, list[ProgressEvent]] = {}

        # Active subscribers: task_id -> Set[asyncio.Queue]
        self._subscribers: Dict[str, Set[asyncio.Queue]] = {}

        # Locks for thread-safety
        self._lock = asyncio.Lock()

        # Retention policy
        self.retention_minutes = retention_minutes

        # Background cleanup task
        self._cleanup_task: Optional[asyncio.Task] = None

        logger.info(f"ProgressTracker initialized: retention={retention_minutes}min")

    async def start(self):
        """Start background tasks"""
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            logger.info("ProgressTracker background tasks started")

    async def stop(self):
        """Stop background tasks"""
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            logger.info("ProgressTracker background tasks stopped")

    async def publish_event(self, task_id: str, event_type: EventType, data: Dict) -> None:
        """
        Publish progress event to all subscribers

        Args:
            task_id: Task identifier
            event_type: Type of event
            data: Event payload
        """
        event = ProgressEvent(
            task_id=task_id,
            event_type=event_type,
            data=data
        )

        async with self._lock:
            # Store in history
            if task_id not in self._progress_history:
                self._progress_history[task_id] = []
            self._progress_history[task_id].append(event)

            # Broadcast to all subscribers
            if task_id in self._subscribers:
                dead_queues = set()
                for queue in self._subscribers[task_id]:
                    try:
                        queue.put_nowait(event)
                    except asyncio.QueueFull:
                        logger.warning(f"Subscriber queue full for task {task_id}, marking for removal")
                        dead_queues.add(queue)
                    except Exception as e:
                        logger.error(f"Failed to publish to subscriber: {e}")
                        dead_queues.add(queue)

                # Remove dead queues
                for queue in dead_queues:
                    self._subscribers[task_id].discard(queue)

        logger.debug(f"Published {event_type.value} event for task {task_id}")

    async def subscribe(self, task_id: str, queue_size: int = 100) -> AsyncIterator[ProgressEvent]:
        """
        Subscribe to progress updates for a task

        Args:
            task_id: Task to subscribe to
            queue_size: Maximum queue size

        Yields:
            ProgressEvent objects as they occur
        """
        queue: asyncio.Queue[ProgressEvent] = asyncio.Queue(maxsize=queue_size)

        # Register subscriber
        async with self._lock:
            if task_id not in self._subscribers:
                self._subscribers[task_id] = set()
            self._subscribers[task_id].add(queue)

            # Send historical events
            if task_id in self._progress_history:
                for event in self._progress_history[task_id]:
                    try:
                        queue.put_nowait(event)
                    except asyncio.QueueFull:
                        logger.warning(f"Queue full during history replay for {task_id}")
                        break

        logger.info(f"New subscriber for task {task_id}")

        try:
            # Heartbeat interval (30 seconds)
            heartbeat_interval = 30
            last_heartbeat = asyncio.get_event_loop().time()

            while True:
                try:
                    # Wait for event with timeout for heartbeat
                    timeout = heartbeat_interval - (asyncio.get_event_loop().time() - last_heartbeat)
                    if timeout <= 0:
                        timeout = heartbeat_interval

                    event = await asyncio.wait_for(queue.get(), timeout=timeout)
                    yield event

                    # Reset heartbeat timer
                    last_heartbeat = asyncio.get_event_loop().time()

                except asyncio.TimeoutError:
                    # Send heartbeat
                    heartbeat_event = ProgressEvent(
                        task_id=task_id,
                        event_type=EventType.HEARTBEAT,
                        data={"message": "keepalive"}
                    )
                    yield heartbeat_event
                    last_heartbeat = asyncio.get_event_loop().time()

        except GeneratorExit:
            logger.info(f"Subscriber disconnected from task {task_id}")
        finally:
            # Cleanup subscriber
            async with self._lock:
                if task_id in self._subscribers:
                    self._subscribers[task_id].discard(queue)
                    if not self._subscribers[task_id]:
                        del self._subscribers[task_id]

    def get_progress_history(self, task_id: str) -> list[ProgressEvent]:
        """Get historical progress events for a task"""
        return self._progress_history.get(task_id, [])

    def get_latest_progress(self, task_id: str) -> Optional[ProgressEvent]:
        """Get latest progress event for a task"""
        history = self._progress_history.get(task_id, [])
        return history[-1] if history else None

    def get_active_tasks(self) -> list[str]:
        """Get list of tasks with active subscribers"""
        return list(self._subscribers.keys())

    def get_subscriber_count(self, task_id: str) -> int:
        """Get number of active subscribers for a task"""
        return len(self._subscribers.get(task_id, set()))

    async def _cleanup_loop(self):
        """Background task to cleanup old progress data"""
        while True:
            try:
                await asyncio.sleep(300)  # Run every 5 minutes

                cutoff_time = datetime.utcnow() - timedelta(minutes=self.retention_minutes)
                removed_tasks = []

                async with self._lock:
                    for task_id, events in list(self._progress_history.items()):
                        # Remove events older than retention period
                        filtered_events = [e for e in events if e.timestamp > cutoff_time]

                        if not filtered_events:
                            # No events left, remove task if no active subscribers
                            if task_id not in self._subscribers:
                                del self._progress_history[task_id]
                                removed_tasks.append(task_id)
                        else:
                            self._progress_history[task_id] = filtered_events

                if removed_tasks:
                    logger.info(f"Cleaned up progress history for {len(removed_tasks)} tasks")

            except asyncio.CancelledError:
                logger.info("Cleanup loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")


# ============================================================================
# Singleton Instance
# ============================================================================

progress_tracker = ProgressTracker()
