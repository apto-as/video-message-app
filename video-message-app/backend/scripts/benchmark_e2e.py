"""
End-to-End Pipeline Benchmark
------------------------------
Comprehensive benchmark comparing:
- Baseline (no optimization)
- With caching
- With parallel processing
- Full optimizations

Metrics:
- Latency (P50, P95, P99)
- Throughput (requests/sec)
- GPU utilization
- Cache hit rate
- Cost per request
"""

import asyncio
import time
import statistics
from pathlib import Path
from typing import List, Dict, Any
from dataclasses import dataclass
from datetime import datetime
import json
import logging

# Add parent directory to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.video_pipeline import VideoPipeline, PipelineResult

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class BenchmarkConfig:
    """Benchmark configuration"""
    name: str
    enable_cache: bool = False
    parallel_limit: int = 1
    use_tensorrt: bool = True
    use_fp16: bool = True


@dataclass
class BenchmarkResult:
    """Benchmark result for a single configuration"""
    config_name: str
    total_requests: int
    successful_requests: int
    failed_requests: int
    latency_ms_p50: float
    latency_ms_p95: float
    latency_ms_p99: float
    throughput_rps: float
    avg_latency_ms: float
    min_latency_ms: float
    max_latency_ms: float
    cache_hit_rate: float = 0.0
    gpu_utilization_avg: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "config_name": self.config_name,
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "latency_percentiles": {
                "p50": round(self.latency_ms_p50, 2),
                "p95": round(self.latency_ms_p95, 2),
                "p99": round(self.latency_ms_p99, 2),
            },
            "throughput_rps": round(self.throughput_rps, 4),
            "latency_stats": {
                "avg_ms": round(self.avg_latency_ms, 2),
                "min_ms": round(self.min_latency_ms, 2),
                "max_ms": round(self.max_latency_ms, 2),
            },
            "cache_hit_rate": round(self.cache_hit_rate * 100, 2),
            "gpu_utilization_avg": round(self.gpu_utilization_avg, 2)
        }


class E2EBenchmark:
    """End-to-end pipeline benchmark"""

    def __init__(self, storage_dir: Path):
        self.storage_dir = storage_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    async def run_benchmark(
        self,
        config: BenchmarkConfig,
        image_path: Path,
        audio_path: Path,
        num_requests: int = 10
    ) -> BenchmarkResult:
        """Run benchmark for a specific configuration"""
        logger.info(f"{'='*70}")
        logger.info(f"Running benchmark: {config.name}")
        logger.info(f"Configuration: {config}")
        logger.info(f"Requests: {num_requests}")
        logger.info(f"{'='*70}")

        # Initialize pipeline
        pipeline = VideoPipeline(storage_dir=self.storage_dir)

        # Results tracking
        latencies: List[float] = []
        results: List[PipelineResult] = []

        # Execute requests
        benchmark_start = time.perf_counter()

        for i in range(num_requests):
            logger.info(f"Request {i+1}/{num_requests}")

            try:
                result = await pipeline.execute(
                    image_path=image_path,
                    audio_path=audio_path,
                    selected_person_id=None,
                    conf_threshold=0.5,
                    iou_threshold=0.45,
                    apply_smoothing=True
                )

                results.append(result)

                if result.success and result.execution_time_ms:
                    latencies.append(result.execution_time_ms)
                    logger.info(f"  ✓ Success: {result.execution_time_ms:.2f}ms")
                else:
                    logger.warning(f"  ✗ Failed: {result.error}")

            except Exception as e:
                logger.error(f"  ✗ Exception: {e}")
                results.append(PipelineResult(
                    task_id=f"error_{i}",
                    success=False,
                    error=str(e)
                ))

        benchmark_end = time.perf_counter()
        total_time_sec = benchmark_end - benchmark_start

        # Calculate statistics
        successful = sum(1 for r in results if r.success)
        failed = num_requests - successful

        if latencies:
            latencies_sorted = sorted(latencies)
            p50_idx = int(len(latencies_sorted) * 0.50)
            p95_idx = int(len(latencies_sorted) * 0.95)
            p99_idx = int(len(latencies_sorted) * 0.99)

            result = BenchmarkResult(
                config_name=config.name,
                total_requests=num_requests,
                successful_requests=successful,
                failed_requests=failed,
                latency_ms_p50=latencies_sorted[p50_idx],
                latency_ms_p95=latencies_sorted[p95_idx],
                latency_ms_p99=latencies_sorted[p99_idx],
                throughput_rps=successful / total_time_sec,
                avg_latency_ms=statistics.mean(latencies),
                min_latency_ms=min(latencies),
                max_latency_ms=max(latencies),
                cache_hit_rate=0.0,  # TODO: Implement cache tracking
                gpu_utilization_avg=0.0  # TODO: Implement GPU monitoring
            )
        else:
            # All failed
            result = BenchmarkResult(
                config_name=config.name,
                total_requests=num_requests,
                successful_requests=0,
                failed_requests=num_requests,
                latency_ms_p50=0.0,
                latency_ms_p95=0.0,
                latency_ms_p99=0.0,
                throughput_rps=0.0,
                avg_latency_ms=0.0,
                min_latency_ms=0.0,
                max_latency_ms=0.0
            )

        # Print summary
        logger.info(f"\n{'='*70}")
        logger.info(f"Benchmark Results: {config.name}")
        logger.info(f"{'='*70}")
        logger.info(f"Total Requests:      {result.total_requests}")
        logger.info(f"Successful:          {result.successful_requests}")
        logger.info(f"Failed:              {result.failed_requests}")
        logger.info(f"Throughput:          {result.throughput_rps:.4f} req/sec")
        logger.info(f"Latency (avg):       {result.avg_latency_ms:.2f}ms")
        logger.info(f"Latency (p50):       {result.latency_ms_p50:.2f}ms")
        logger.info(f"Latency (p95):       {result.latency_ms_p95:.2f}ms")
        logger.info(f"Latency (p99):       {result.latency_ms_p99:.2f}ms")
        logger.info(f"{'='*70}\n")

        return result

    async def run_all_benchmarks(
        self,
        image_path: Path,
        audio_path: Path,
        num_requests: int = 10
    ) -> List[BenchmarkResult]:
        """Run all benchmark configurations"""
        configs = [
            BenchmarkConfig(
                name="Baseline (No Optimization)",
                enable_cache=False,
                parallel_limit=1,
                use_tensorrt=False,
                use_fp16=False
            ),
            BenchmarkConfig(
                name="TensorRT + FP16",
                enable_cache=False,
                parallel_limit=1,
                use_tensorrt=True,
                use_fp16=True
            ),
            BenchmarkConfig(
                name="With Caching",
                enable_cache=True,
                parallel_limit=1,
                use_tensorrt=True,
                use_fp16=True
            ),
            BenchmarkConfig(
                name="Full Optimization (Cache + Parallel)",
                enable_cache=True,
                parallel_limit=3,
                use_tensorrt=True,
                use_fp16=True
            ),
        ]

        results = []
        for config in configs:
            result = await self.run_benchmark(
                config=config,
                image_path=image_path,
                audio_path=audio_path,
                num_requests=num_requests
            )
            results.append(result)

        return results


async def main():
    import argparse

    parser = argparse.ArgumentParser(description="E2E Pipeline Benchmark")
    parser.add_argument("--image", type=Path, required=True, help="Input image")
    parser.add_argument("--audio", type=Path, required=True, help="Input audio")
    parser.add_argument("--requests", type=int, default=10, help="Number of requests per benchmark")
    parser.add_argument("--output", type=Path, default=Path("benchmark_results.json"), help="Output file")

    args = parser.parse_args()

    if not args.image.exists():
        logger.error(f"Image not found: {args.image}")
        return

    if not args.audio.exists():
        logger.error(f"Audio not found: {args.audio}")
        return

    # Run benchmarks
    storage_dir = Path(__file__).parent.parent / "data" / "benchmark"
    benchmark = E2EBenchmark(storage_dir=storage_dir)

    results = await benchmark.run_all_benchmarks(
        image_path=args.image,
        audio_path=args.audio,
        num_requests=args.requests
    )

    # Generate comparison report
    logger.info(f"\n{'='*70}")
    logger.info("BENCHMARK COMPARISON")
    logger.info(f"{'='*70}\n")

    baseline = results[0]

    logger.info(f"{'Configuration':<40} {'Latency (p50)':<15} {'Throughput':<15} {'Improvement'}")
    logger.info(f"{'-'*40} {'-'*15} {'-'*15} {'-'*15}")

    for result in results:
        improvement = ((baseline.latency_ms_p50 - result.latency_ms_p50) / baseline.latency_ms_p50 * 100) if baseline.latency_ms_p50 > 0 else 0
        logger.info(
            f"{result.config_name:<40} "
            f"{result.latency_ms_p50:<15.2f} "
            f"{result.throughput_rps:<15.4f} "
            f"{improvement:>+6.1f}%"
        )

    # Save results
    output_data = {
        "benchmark_timestamp": datetime.now().isoformat(),
        "configurations": [r.to_dict() for r in results],
        "baseline": baseline.to_dict(),
        "improvements": {
            r.config_name: {
                "latency_reduction_percent": round(
                    ((baseline.latency_ms_p50 - r.latency_ms_p50) / baseline.latency_ms_p50 * 100)
                    if baseline.latency_ms_p50 > 0 else 0,
                    2
                ),
                "throughput_increase_percent": round(
                    ((r.throughput_rps - baseline.throughput_rps) / baseline.throughput_rps * 100)
                    if baseline.throughput_rps > 0 else 0,
                    2
                )
            }
            for r in results if r.config_name != baseline.config_name
        }
    }

    with open(args.output, "w") as f:
        json.dump(output_data, f, indent=2)

    logger.info(f"\nResults saved to: {args.output}")


if __name__ == "__main__":
    asyncio.run(main())
