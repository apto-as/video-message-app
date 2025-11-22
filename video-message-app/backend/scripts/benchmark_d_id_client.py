"""
Performance benchmark for D-ID API Client
Compares original vs optimized implementation
"""

import asyncio
import time
import statistics
from typing import List, Dict, Any
from pathlib import Path
import sys

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.d_id_client import DIdClient
from services.d_id_client_optimized import OptimizedDIdClient, Priority


class BenchmarkResults:
    """Store and analyze benchmark results"""

    def __init__(self, name: str):
        self.name = name
        self.durations: List[float] = []
        self.errors: int = 0
        self.start_time: float = 0
        self.end_time: float = 0

    def record_duration(self, duration: float):
        """Record a single operation duration"""
        self.durations.append(duration)

    def record_error(self):
        """Record an error"""
        self.errors += 1

    @property
    def total_time(self) -> float:
        """Total execution time"""
        return self.end_time - self.start_time

    @property
    def success_count(self) -> int:
        """Number of successful operations"""
        return len(self.durations)

    @property
    def total_count(self) -> int:
        """Total number of operations"""
        return self.success_count + self.errors

    @property
    def error_rate(self) -> float:
        """Error rate percentage"""
        if self.total_count == 0:
            return 0.0
        return (self.errors / self.total_count) * 100

    @property
    def throughput(self) -> float:
        """Operations per second"""
        if self.total_time == 0:
            return 0.0
        return self.success_count / self.total_time

    @property
    def avg_duration(self) -> float:
        """Average operation duration"""
        if not self.durations:
            return 0.0
        return statistics.mean(self.durations)

    @property
    def median_duration(self) -> float:
        """Median operation duration"""
        if not self.durations:
            return 0.0
        return statistics.median(self.durations)

    @property
    def p95_duration(self) -> float:
        """95th percentile duration"""
        if not self.durations:
            return 0.0
        sorted_durations = sorted(self.durations)
        index = int(len(sorted_durations) * 0.95)
        return sorted_durations[min(index, len(sorted_durations) - 1)]

    @property
    def p99_duration(self) -> float:
        """99th percentile duration"""
        if not self.durations:
            return 0.0
        sorted_durations = sorted(self.durations)
        index = int(len(sorted_durations) * 0.99)
        return sorted_durations[min(index, len(sorted_durations) - 1)]

    def summary(self) -> Dict[str, Any]:
        """Get summary statistics"""
        return {
            "name": self.name,
            "total_operations": self.total_count,
            "successful_operations": self.success_count,
            "errors": self.errors,
            "error_rate_%": round(self.error_rate, 2),
            "total_time_s": round(self.total_time, 2),
            "throughput_ops/s": round(self.throughput, 2),
            "avg_duration_ms": round(self.avg_duration * 1000, 2),
            "median_duration_ms": round(self.median_duration * 1000, 2),
            "p95_duration_ms": round(self.p95_duration * 1000, 2),
            "p99_duration_ms": round(self.p99_duration * 1000, 2),
        }

    def print_summary(self):
        """Print summary statistics"""
        summary = self.summary()

        print(f"\n{'='*60}")
        print(f"Benchmark Results: {self.name}")
        print(f"{'='*60}")

        for key, value in summary.items():
            if key != "name":
                print(f"  {key:30s}: {value}")

        print(f"{'='*60}\n")


async def benchmark_get_stats(client, results: BenchmarkResults, iterations: int):
    """Benchmark get_stats operation"""
    print(f"  Testing get_stats ({iterations} iterations)...")

    for i in range(iterations):
        start = time.time()
        try:
            await client.get_stats()
            duration = time.time() - start
            results.record_duration(duration)
        except Exception as e:
            print(f"    Error in iteration {i}: {e}")
            results.record_error()

        # Small delay between requests
        await asyncio.sleep(0.01)


async def benchmark_concurrent_get_stats(
    client,
    results: BenchmarkResults,
    concurrent_requests: int
):
    """Benchmark concurrent get_stats operations"""
    print(f"  Testing concurrent get_stats ({concurrent_requests} concurrent)...")

    async def single_request():
        start = time.time()
        try:
            await client.get_stats()
            duration = time.time() - start
            results.record_duration(duration)
        except Exception as e:
            print(f"    Error: {e}")
            results.record_error()

    # Execute all requests concurrently
    tasks = [single_request() for _ in range(concurrent_requests)]
    await asyncio.gather(*tasks)


async def benchmark_rate_limiter(results: BenchmarkResults, max_concurrent: int):
    """Benchmark rate limiter acquire/release"""
    from services.rate_limiter import RateLimiter

    print(f"  Testing rate limiter ({max_concurrent} concurrent)...")

    rate_limiter = RateLimiter(max_concurrent=max_concurrent)

    async def acquire_release():
        start = time.time()
        try:
            request_id = await rate_limiter.acquire(
                priority=Priority.NORMAL,
                timeout=5.0
            )
            # Simulate work
            await asyncio.sleep(0.01)
            await rate_limiter.release(request_id)

            duration = time.time() - start
            results.record_duration(duration)
        except Exception as e:
            print(f"    Error: {e}")
            results.record_error()

    # Execute concurrent requests
    tasks = [acquire_release() for _ in range(max_concurrent * 2)]
    await asyncio.gather(*tasks)


async def run_benchmarks():
    """Run all benchmarks"""
    print("\n" + "="*60)
    print("D-ID API Client Performance Benchmark")
    print("="*60 + "\n")

    # Configuration
    iterations = 50
    concurrent_requests = 10

    # Original client benchmark
    print("Benchmarking Original D-ID Client...")
    original_results = BenchmarkResults("Original DIdClient")
    original_client = DIdClient()

    original_results.start_time = time.time()
    await benchmark_get_stats(original_client, original_results, iterations)
    original_results.end_time = time.time()

    original_results.print_summary()

    # Optimized client benchmark
    print("Benchmarking Optimized D-ID Client...")
    optimized_results = BenchmarkResults("Optimized DIdClient")
    optimized_client = OptimizedDIdClient(max_concurrent=concurrent_requests)

    optimized_results.start_time = time.time()
    await benchmark_get_stats(optimized_client, optimized_results, iterations)
    optimized_results.end_time = time.time()

    optimized_results.print_summary()

    # Concurrent requests benchmark
    print("Benchmarking Concurrent Requests (Optimized Client)...")
    concurrent_results = BenchmarkResults(
        f"Optimized DIdClient (Concurrent x{concurrent_requests})"
    )

    concurrent_results.start_time = time.time()
    await benchmark_concurrent_get_stats(
        optimized_client,
        concurrent_results,
        concurrent_requests
    )
    concurrent_results.end_time = time.time()

    concurrent_results.print_summary()

    # Rate limiter benchmark
    print("Benchmarking Rate Limiter...")
    rate_limiter_results = BenchmarkResults("Rate Limiter")

    rate_limiter_results.start_time = time.time()
    await benchmark_rate_limiter(rate_limiter_results, concurrent_requests)
    rate_limiter_results.end_time = time.time()

    rate_limiter_results.print_summary()

    # Comparison
    print_comparison(original_results, optimized_results)

    # Cleanup
    await optimized_client.close()


def print_comparison(original: BenchmarkResults, optimized: BenchmarkResults):
    """Print comparison between original and optimized"""
    print("\n" + "="*60)
    print("Performance Improvement Summary")
    print("="*60 + "\n")

    def calculate_improvement(original_val, optimized_val) -> str:
        if original_val == 0:
            return "N/A"
        improvement = ((original_val - optimized_val) / original_val) * 100
        if improvement > 0:
            return f"+{improvement:.1f}% faster"
        else:
            return f"{abs(improvement):.1f}% slower"

    metrics = [
        ("Throughput", "throughput_ops/s", "higher is better"),
        ("Average Duration", "avg_duration_ms", "lower is better"),
        ("Median Duration", "median_duration_ms", "lower is better"),
        ("P95 Duration", "p95_duration_ms", "lower is better"),
        ("P99 Duration", "p99_duration_ms", "lower is better"),
    ]

    for metric_name, metric_key, direction in metrics:
        original_val = original.summary()[metric_key]
        optimized_val = optimized.summary()[metric_key]

        if "higher" in direction:
            improvement = calculate_improvement(
                1/original_val if original_val else 0,
                1/optimized_val if optimized_val else 0
            )
        else:
            improvement = calculate_improvement(original_val, optimized_val)

        print(f"  {metric_name:20s}: {original_val:8.2f} → {optimized_val:8.2f} ({improvement})")

    print("\n" + "="*60 + "\n")


def main():
    """Main entry point"""
    try:
        asyncio.run(run_benchmarks())
    except KeyboardInterrupt:
        print("\nBenchmark interrupted by user")
    except Exception as e:
        print(f"\nBenchmark failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
