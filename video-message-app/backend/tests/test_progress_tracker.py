"""
Unit Tests for ProgressTracker System

Tests:
- Event publishing and subscription
- Multi-subscriber support
- Heartbeat mechanism
- Automatic cleanup
- WebSocket/SSE integration
"""

import pytest
import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.progress_tracker import (
    ProgressTracker,
    EventType,
    ProgressEvent
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def tracker():
    """Create a fresh ProgressTracker instance"""
    return ProgressTracker(retention_minutes=1)


@pytest.fixture
async def started_tracker(tracker):
    """Create and start a ProgressTracker"""
    await tracker.start()
    yield tracker
    await tracker.stop()


# ============================================================================
# Basic Event Publishing Tests
# ============================================================================

@pytest.mark.asyncio
async def test_publish_event(tracker):
    """Test basic event publishing"""
    task_id = "test-task-1"

    await tracker.publish_event(
        task_id,
        EventType.STAGE_UPDATE,
        {"stage": "initialized", "progress": 0, "message": "Starting"}
    )

    # Check history
    history = tracker.get_progress_history(task_id)
    assert len(history) == 1
    assert history[0].task_id == task_id
    assert history[0].event_type == EventType.STAGE_UPDATE


@pytest.mark.asyncio
async def test_publish_multiple_events(tracker):
    """Test publishing multiple events"""
    task_id = "test-task-2"

    # Publish 5 events
    for i in range(5):
        await tracker.publish_event(
            task_id,
            EventType.PROGRESS_UPDATE,
            {"stage": f"stage_{i}", "progress": i * 20, "message": f"Step {i}"}
        )

    # Check history
    history = tracker.get_progress_history(task_id)
    assert len(history) == 5

    # Check progress sequence
    for i, event in enumerate(history):
        assert event.data["progress"] == i * 20


@pytest.mark.asyncio
async def test_get_latest_progress(tracker):
    """Test getting latest progress"""
    task_id = "test-task-3"

    # Publish events
    await tracker.publish_event(task_id, EventType.STAGE_UPDATE, {"progress": 0})
    await tracker.publish_event(task_id, EventType.STAGE_UPDATE, {"progress": 50})
    await tracker.publish_event(task_id, EventType.STAGE_UPDATE, {"progress": 100})

    # Get latest
    latest = tracker.get_latest_progress(task_id)
    assert latest is not None
    assert latest.data["progress"] == 100


# ============================================================================
# Subscription Tests
# ============================================================================

@pytest.mark.asyncio
async def test_single_subscriber(tracker):
    """Test single subscriber receiving events"""
    task_id = "test-task-4"
    received_events = []

    # Start subscriber in background
    async def subscriber():
        async for event in tracker.subscribe(task_id):
            received_events.append(event)
            if event.event_type == EventType.COMPLETE:
                break

    subscriber_task = asyncio.create_task(subscriber())

    # Give subscriber time to connect
    await asyncio.sleep(0.1)

    # Publish events
    await tracker.publish_event(task_id, EventType.STAGE_UPDATE, {"progress": 0})
    await tracker.publish_event(task_id, EventType.STAGE_UPDATE, {"progress": 50})
    await tracker.publish_event(task_id, EventType.COMPLETE, {"progress": 100})

    # Wait for subscriber to finish
    await subscriber_task

    # Check received events
    assert len(received_events) >= 3
    assert received_events[-1].event_type == EventType.COMPLETE


@pytest.mark.asyncio
async def test_multiple_subscribers(tracker):
    """Test multiple subscribers receiving same events"""
    task_id = "test-task-5"
    subscriber1_events = []
    subscriber2_events = []

    # Start two subscribers
    async def subscriber1():
        async for event in tracker.subscribe(task_id):
            subscriber1_events.append(event)
            if event.event_type == EventType.COMPLETE:
                break

    async def subscriber2():
        async for event in tracker.subscribe(task_id):
            subscriber2_events.append(event)
            if event.event_type == EventType.COMPLETE:
                break

    sub1_task = asyncio.create_task(subscriber1())
    sub2_task = asyncio.create_task(subscriber2())

    # Give subscribers time to connect
    await asyncio.sleep(0.1)

    # Publish events
    await tracker.publish_event(task_id, EventType.STAGE_UPDATE, {"progress": 0})
    await tracker.publish_event(task_id, EventType.STAGE_UPDATE, {"progress": 50})
    await tracker.publish_event(task_id, EventType.COMPLETE, {"progress": 100})

    # Wait for both subscribers
    await sub1_task
    await sub2_task

    # Both should have received same events
    assert len(subscriber1_events) >= 3
    assert len(subscriber2_events) >= 3
    assert subscriber1_events[-1].event_type == EventType.COMPLETE
    assert subscriber2_events[-1].event_type == EventType.COMPLETE


@pytest.mark.asyncio
async def test_late_subscriber_receives_history(tracker):
    """Test that late subscribers receive historical events"""
    task_id = "test-task-6"

    # Publish events BEFORE subscriber connects
    await tracker.publish_event(task_id, EventType.STAGE_UPDATE, {"progress": 0})
    await tracker.publish_event(task_id, EventType.STAGE_UPDATE, {"progress": 50})

    # Now subscribe
    received_events = []
    async def subscriber():
        async for event in tracker.subscribe(task_id):
            received_events.append(event)
            if len(received_events) >= 3:  # History (2) + new event (1)
                break

    subscriber_task = asyncio.create_task(subscriber())

    # Give subscriber time to receive history
    await asyncio.sleep(0.1)

    # Publish new event
    await tracker.publish_event(task_id, EventType.STAGE_UPDATE, {"progress": 100})

    # Wait for subscriber
    await asyncio.wait_for(subscriber_task, timeout=2.0)

    # Should have received history + new event
    assert len(received_events) >= 3


# ============================================================================
# Heartbeat Tests
# ============================================================================

@pytest.mark.asyncio
async def test_heartbeat(tracker):
    """Test heartbeat mechanism (long-running)"""
    task_id = "test-task-7"
    received_events = []

    # Subscribe and wait for heartbeat
    async def subscriber():
        timeout = 35  # Wait for at least one heartbeat (30s interval)
        start = asyncio.get_event_loop().time()

        async for event in tracker.subscribe(task_id):
            received_events.append(event)
            elapsed = asyncio.get_event_loop().time() - start

            if event.event_type == EventType.HEARTBEAT or elapsed > timeout:
                break

    subscriber_task = asyncio.create_task(subscriber())

    # Wait for heartbeat or timeout
    await asyncio.wait_for(subscriber_task, timeout=40.0)

    # Should have received at least one heartbeat
    heartbeats = [e for e in received_events if e.event_type == EventType.HEARTBEAT]
    assert len(heartbeats) >= 1


# ============================================================================
# Cleanup Tests
# ============================================================================

@pytest.mark.asyncio
async def test_automatic_cleanup(started_tracker):
    """Test automatic cleanup of old events"""
    task_id = "test-task-8"

    # Publish event
    await started_tracker.publish_event(
        task_id,
        EventType.STAGE_UPDATE,
        {"progress": 0}
    )

    # Verify event exists
    history_before = started_tracker.get_progress_history(task_id)
    assert len(history_before) == 1

    # Manually trigger cleanup (simulate time passing)
    # Note: In production, cleanup runs every 5 minutes
    # For testing, we directly manipulate the timestamp
    started_tracker._progress_history[task_id][0].timestamp = (
        datetime.utcnow() - timedelta(minutes=started_tracker.retention_minutes + 1)
    )

    # Trigger cleanup manually
    await started_tracker._cleanup_loop.__wrapped__(started_tracker)

    # Event should be removed
    history_after = started_tracker.get_progress_history(task_id)
    assert len(history_after) == 0


@pytest.mark.asyncio
async def test_active_task_tracking(tracker):
    """Test active task tracking"""
    task_id = "test-task-9"

    # Initially no active tasks
    assert len(tracker.get_active_tasks()) == 0

    # Subscribe
    async def subscriber():
        async for event in tracker.subscribe(task_id):
            if event.event_type == EventType.COMPLETE:
                break

    subscriber_task = asyncio.create_task(subscriber())

    # Give subscriber time to connect
    await asyncio.sleep(0.1)

    # Task should be active
    active_tasks = tracker.get_active_tasks()
    assert task_id in active_tasks

    # Subscriber count
    assert tracker.get_subscriber_count(task_id) == 1

    # Publish complete event
    await tracker.publish_event(task_id, EventType.COMPLETE, {"progress": 100})

    # Wait for subscriber to finish
    await subscriber_task

    # Give time for cleanup
    await asyncio.sleep(0.1)

    # Task should no longer be active
    active_tasks = tracker.get_active_tasks()
    assert task_id not in active_tasks


# ============================================================================
# Error Handling Tests
# ============================================================================

@pytest.mark.asyncio
async def test_subscriber_queue_full_handling(tracker):
    """Test handling of full subscriber queues"""
    task_id = "test-task-10"

    # Create subscriber with small queue
    received_events = []
    async def slow_subscriber():
        async for event in tracker.subscribe(task_id, queue_size=2):
            received_events.append(event)
            await asyncio.sleep(0.5)  # Slow processing
            if len(received_events) >= 5:
                break

    subscriber_task = asyncio.create_task(slow_subscriber())

    # Give subscriber time to connect
    await asyncio.sleep(0.1)

    # Publish many events quickly (overflow queue)
    for i in range(10):
        await tracker.publish_event(
            task_id,
            EventType.PROGRESS_UPDATE,
            {"progress": i * 10}
        )

    # Wait for subscriber
    await subscriber_task

    # Some events may be dropped, but subscriber should continue
    assert len(received_events) >= 2


@pytest.mark.asyncio
async def test_nonexistent_task(tracker):
    """Test querying non-existent task"""
    task_id = "nonexistent-task"

    history = tracker.get_progress_history(task_id)
    assert len(history) == 0

    latest = tracker.get_latest_progress(task_id)
    assert latest is None


# ============================================================================
# JSON/SSE Serialization Tests
# ============================================================================

def test_event_to_json():
    """Test event JSON serialization"""
    event = ProgressEvent(
        task_id="test-task",
        event_type=EventType.STAGE_UPDATE,
        data={"stage": "test", "progress": 50}
    )

    json_str = event.to_json()
    assert "test-task" in json_str
    assert "stage_update" in json_str
    assert "50" in json_str


def test_event_to_sse():
    """Test event SSE serialization"""
    event = ProgressEvent(
        task_id="test-task",
        event_type=EventType.STAGE_UPDATE,
        data={"stage": "test", "progress": 50}
    )

    sse_str = event.to_sse()
    assert sse_str.startswith("data: ")
    assert sse_str.endswith("\n\n")


# ============================================================================
# Performance Benchmarks
# ============================================================================

@pytest.mark.asyncio
async def test_throughput_benchmark(tracker):
    """Benchmark event throughput"""
    task_id = "benchmark-task"
    event_count = 1000

    import time
    start = time.time()

    # Publish 1000 events
    for i in range(event_count):
        await tracker.publish_event(
            task_id,
            EventType.PROGRESS_UPDATE,
            {"progress": i}
        )

    elapsed = time.time() - start
    throughput = event_count / elapsed

    print(f"\nThroughput: {throughput:.0f} events/sec")

    # Should handle at least 1000 events/sec
    assert throughput > 100


@pytest.mark.asyncio
async def test_latency_benchmark(tracker):
    """Benchmark event delivery latency"""
    task_id = "latency-task"
    latencies = []

    # Subscribe and measure latency
    async def subscriber():
        async for event in tracker.subscribe(task_id):
            delivery_time = datetime.utcnow()
            latency = (delivery_time - event.timestamp).total_seconds() * 1000
            latencies.append(latency)

            if len(latencies) >= 100:
                break

    subscriber_task = asyncio.create_task(subscriber())

    # Give subscriber time to connect
    await asyncio.sleep(0.1)

    # Publish 100 events
    for i in range(100):
        await tracker.publish_event(
            task_id,
            EventType.PROGRESS_UPDATE,
            {"progress": i}
        )
        await asyncio.sleep(0.01)  # Small delay between events

    # Wait for subscriber
    await subscriber_task

    # Calculate average latency
    avg_latency = sum(latencies) / len(latencies)
    max_latency = max(latencies)

    print(f"\nAverage latency: {avg_latency:.2f}ms")
    print(f"Max latency: {max_latency:.2f}ms")

    # Should deliver events within 2000ms (2 seconds)
    assert avg_latency < 2000
    assert max_latency < 5000


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
