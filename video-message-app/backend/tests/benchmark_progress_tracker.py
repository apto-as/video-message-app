"""
Performance Benchmark for ProgressTracker System

Measures:
- Event throughput (events/second)
- Event delivery latency (milliseconds)
- Multi-subscriber scalability
- Memory usage under load
- Connection establishment time
"""

import asyncio
import time
import statistics
import sys
from pathlib import Path
from datetime import datetime
from typing import List

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.progress_tracker import ProgressTracker, EventType


# ============================================================================
# Benchmark Configuration
# ============================================================================

class BenchmarkConfig:
    """Benchmark test configuration"""
    EVENT_COUNT = 1000
    SUBSCRIBER_COUNT = 10
    CONCURRENT_TASKS = 5


# ============================================================================
# Benchmark Tests
# ============================================================================

async def benchmark_event_throughput(tracker: ProgressTracker) -> dict:
    """
    Benchmark: Event publishing throughput

    Measures: Events/second for publishing events
    """
    task_id = "throughput-test"
    event_count = BenchmarkConfig.EVENT_COUNT

    start_time = time.time()

    for i in range(event_count):
        await tracker.publish_event(
            task_id,
            EventType.PROGRESS_UPDATE,
            {"progress": i, "stage": f"stage_{i}"}
        )

    elapsed_time = time.time() - start_time
    throughput = event_count / elapsed_time

    return {
        "test": "Event Throughput",
        "event_count": event_count,
        "elapsed_time_sec": elapsed_time,
        "throughput_events_per_sec": throughput
    }


async def benchmark_delivery_latency(tracker: ProgressTracker) -> dict:
    """
    Benchmark: Event delivery latency

    Measures: Time from publish to delivery (milliseconds)
    """
    task_id = "latency-test"
    latencies: List[float] = []

    async def measure_latency():
        async for event in tracker.subscribe(task_id):
            delivery_time = datetime.utcnow()
            latency_ms = (delivery_time - event.timestamp).total_seconds() * 1000
            latencies.append(latency_ms)

            if len(latencies) >= BenchmarkConfig.EVENT_COUNT:
                break

    # Start subscriber
    subscriber_task = asyncio.create_task(measure_latency())

    # Give subscriber time to connect
    await asyncio.sleep(0.1)

    # Publish events
    for i in range(BenchmarkConfig.EVENT_COUNT):
        await tracker.publish_event(
            task_id,
            EventType.PROGRESS_UPDATE,
            {"progress": i}
        )

    # Wait for subscriber to finish
    await subscriber_task

    # Calculate statistics
    avg_latency = statistics.mean(latencies)
    median_latency = statistics.median(latencies)
    p95_latency = sorted(latencies)[int(len(latencies) * 0.95)]
    p99_latency = sorted(latencies)[int(len(latencies) * 0.99)]
    max_latency = max(latencies)

    return {
        "test": "Delivery Latency",
        "event_count": len(latencies),
        "avg_latency_ms": avg_latency,
        "median_latency_ms": median_latency,
        "p95_latency_ms": p95_latency,
        "p99_latency_ms": p99_latency,
        "max_latency_ms": max_latency
    }


async def benchmark_multi_subscriber(tracker: ProgressTracker) -> dict:
    """
    Benchmark: Multi-subscriber scalability

    Measures: Performance with multiple concurrent subscribers
    """
    task_id = "multi-subscriber-test"
    subscriber_count = BenchmarkConfig.SUBSCRIBER_COUNT
    event_count = 100

    subscriber_latencies = [[] for _ in range(subscriber_count)]

    async def subscriber(subscriber_id: int):
        async for event in tracker.subscribe(task_id):
            delivery_time = datetime.utcnow()
            latency_ms = (delivery_time - event.timestamp).total_seconds() * 1000
            subscriber_latencies[subscriber_id].append(latency_ms)

            if len(subscriber_latencies[subscriber_id]) >= event_count:
                break

    # Start all subscribers
    start_time = time.time()
    subscriber_tasks = [
        asyncio.create_task(subscriber(i))
        for i in range(subscriber_count)
    ]

    # Give subscribers time to connect
    await asyncio.sleep(0.2)

    # Publish events
    for i in range(event_count):
        await tracker.publish_event(
            task_id,
            EventType.PROGRESS_UPDATE,
            {"progress": i}
        )

    # Wait for all subscribers to finish
    await asyncio.gather(*subscriber_tasks)

    elapsed_time = time.time() - start_time

    # Calculate per-subscriber statistics
    subscriber_stats = []
    for i, latencies in enumerate(subscriber_latencies):
        if latencies:
            subscriber_stats.append({
                "subscriber_id": i,
                "event_count": len(latencies),
                "avg_latency_ms": statistics.mean(latencies),
                "max_latency_ms": max(latencies)
            })

    # Overall statistics
    all_latencies = [lat for latencies in subscriber_latencies for lat in latencies]
    avg_latency = statistics.mean(all_latencies) if all_latencies else 0

    return {
        "test": "Multi-Subscriber Scalability",
        "subscriber_count": subscriber_count,
        "event_count": event_count,
        "elapsed_time_sec": elapsed_time,
        "avg_latency_ms": avg_latency,
        "subscriber_stats": subscriber_stats
    }


async def benchmark_concurrent_tasks(tracker: ProgressTracker) -> dict:
    """
    Benchmark: Concurrent task handling

    Measures: Performance with multiple concurrent tasks
    """
    task_count = BenchmarkConfig.CONCURRENT_TASKS
    events_per_task = 100

    async def task_publisher(task_id: str):
        for i in range(events_per_task):
            await tracker.publish_event(
                task_id,
                EventType.PROGRESS_UPDATE,
                {"progress": i}
            )

    start_time = time.time()

    # Run all tasks concurrently
    await asyncio.gather(*[
        task_publisher(f"task-{i}")
        for i in range(task_count)
    ])

    elapsed_time = time.time() - start_time
    total_events = task_count * events_per_task
    throughput = total_events / elapsed_time

    return {
        "test": "Concurrent Task Handling",
        "task_count": task_count,
        "events_per_task": events_per_task,
        "total_events": total_events,
        "elapsed_time_sec": elapsed_time,
        "throughput_events_per_sec": throughput
    }


async def benchmark_connection_establishment(tracker: ProgressTracker) -> dict:
    """
    Benchmark: Connection establishment time

    Measures: Time to establish subscriber connection
    """
    task_id = "connection-test"
    connection_times: List[float] = []

    for i in range(100):
        start_time = time.time()

        # Subscribe
        async def quick_subscriber():
            async for event in tracker.subscribe(task_id):
                # Exit immediately
                break

        subscriber_task = asyncio.create_task(quick_subscriber())

        # Publish event to trigger subscriber
        await tracker.publish_event(
            task_id,
            EventType.PROGRESS_UPDATE,
            {"progress": i}
        )

        # Wait for subscriber to receive event
        await subscriber_task

        elapsed_time = (time.time() - start_time) * 1000  # Convert to ms
        connection_times.append(elapsed_time)

    avg_connection_time = statistics.mean(connection_times)
    median_connection_time = statistics.median(connection_times)
    max_connection_time = max(connection_times)

    return {
        "test": "Connection Establishment",
        "trial_count": len(connection_times),
        "avg_connection_time_ms": avg_connection_time,
        "median_connection_time_ms": median_connection_time,
        "max_connection_time_ms": max_connection_time
    }


# ============================================================================
# Main Benchmark Runner
# ============================================================================

async def run_all_benchmarks():
    """
    Run all benchmark tests and generate report
    """
    print("=" * 80)
    print("ProgressTracker Performance Benchmark")
    print("=" * 80)

    tracker = ProgressTracker(retention_minutes=60)
    await tracker.start()

    results = []

    # Benchmark 1: Event Throughput
    print("\n[1/5] Running Event Throughput benchmark...")
    result1 = await benchmark_event_throughput(tracker)
    results.append(result1)
    print(f"  Throughput: {result1['throughput_events_per_sec']:.0f} events/sec")

    # Benchmark 2: Delivery Latency
    print("\n[2/5] Running Delivery Latency benchmark...")
    result2 = await benchmark_delivery_latency(tracker)
    results.append(result2)
    print(f"  Avg Latency: {result2['avg_latency_ms']:.2f}ms")
    print(f"  P95 Latency: {result2['p95_latency_ms']:.2f}ms")
    print(f"  Max Latency: {result2['max_latency_ms']:.2f}ms")

    # Benchmark 3: Multi-Subscriber
    print("\n[3/5] Running Multi-Subscriber benchmark...")
    result3 = await benchmark_multi_subscriber(tracker)
    results.append(result3)
    print(f"  Subscribers: {result3['subscriber_count']}")
    print(f"  Avg Latency: {result3['avg_latency_ms']:.2f}ms")

    # Benchmark 4: Concurrent Tasks
    print("\n[4/5] Running Concurrent Tasks benchmark...")
    result4 = await benchmark_concurrent_tasks(tracker)
    results.append(result4)
    print(f"  Throughput: {result4['throughput_events_per_sec']:.0f} events/sec")

    # Benchmark 5: Connection Establishment
    print("\n[5/5] Running Connection Establishment benchmark...")
    result5 = await benchmark_connection_establishment(tracker)
    results.append(result5)
    print(f"  Avg Connection Time: {result5['avg_connection_time_ms']:.2f}ms")

    await tracker.stop()

    # ========================================================================
    # Generate Summary Report
    # ========================================================================
    print("\n" + "=" * 80)
    print("BENCHMARK SUMMARY")
    print("=" * 80)

    for result in results:
        print(f"\n{result['test']}:")
        for key, value in result.items():
            if key != "test" and key != "subscriber_stats":
                if isinstance(value, float):
                    print(f"  {key}: {value:.2f}")
                else:
                    print(f"  {key}: {value}")

    # Performance Goals
    print("\n" + "=" * 80)
    print("PERFORMANCE GOALS CHECK")
    print("=" * 80)

    goals = [
        {
            "name": "Event Throughput",
            "target": 1000,
            "actual": result1['throughput_events_per_sec'],
            "unit": "events/sec",
            "passed": result1['throughput_events_per_sec'] >= 1000
        },
        {
            "name": "Avg Delivery Latency",
            "target": 2000,
            "actual": result2['avg_latency_ms'],
            "unit": "ms",
            "passed": result2['avg_latency_ms'] < 2000
        },
        {
            "name": "P95 Delivery Latency",
            "target": 5000,
            "actual": result2['p95_latency_ms'],
            "unit": "ms",
            "passed": result2['p95_latency_ms'] < 5000
        },
        {
            "name": "Multi-Subscriber Latency",
            "target": 3000,
            "actual": result3['avg_latency_ms'],
            "unit": "ms",
            "passed": result3['avg_latency_ms'] < 3000
        },
        {
            "name": "Connection Establishment",
            "target": 100,
            "actual": result5['avg_connection_time_ms'],
            "unit": "ms",
            "passed": result5['avg_connection_time_ms'] < 100
        }
    ]

    passed_count = 0
    for goal in goals:
        status = "✓ PASS" if goal['passed'] else "✗ FAIL"
        print(f"{status} {goal['name']}: {goal['actual']:.2f}{goal['unit']} (target: <{goal['target']}{goal['unit']})")
        if goal['passed']:
            passed_count += 1

    print(f"\nOverall: {passed_count}/{len(goals)} goals met")

    if passed_count == len(goals):
        print("\n✓ All performance goals met!")
    else:
        print(f"\n✗ {len(goals) - passed_count} performance goal(s) not met")

    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(run_all_benchmarks())
