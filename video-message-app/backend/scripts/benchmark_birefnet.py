"""BiRefNet performance benchmark on EC2 Tesla T4"""
import time
import torch
import numpy as np
import cv2
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.background_remover import BackgroundRemover


def benchmark(model_dir: str, num_runs: int = 100, warmup_runs: int = 10):
    """Benchmark BiRefNet inference latency

    Args:
        model_dir: Path to BiRefNet model directory
        num_runs: Number of benchmark iterations
        warmup_runs: Number of warmup iterations
    """
    print(f"BiRefNet Performance Benchmark")
    print(f"=" * 60)
    print(f"Model: BiRefNet-portrait (safetensors)")
    print(f"Device: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'}")
    print(f"Runs: {num_runs} (warmup: {warmup_runs})")
    print(f"=" * 60)

    # Initialize background remover
    print("\nInitializing model...")
    remover = BackgroundRemover(
        model_dir,
        device="cuda",
        use_tensorrt=True,
        use_fp16=True
    )

    # Create dummy image (1920x1080 portrait)
    dummy_image = np.random.randint(0, 255, (1080, 1920, 3), dtype=np.uint8)
    temp_path = Path("/tmp/benchmark_input.jpg")
    cv2.imwrite(str(temp_path), dummy_image)

    print(f"\nConfiguration:")
    print(f"  Device: {remover.device}")
    print(f"  TensorRT: {remover.use_tensorrt}")
    print(f"  FP16: {remover.use_fp16}")
    print(f"  Input size: {remover.input_size}")

    # Warmup
    print(f"\nWarming up ({warmup_runs} runs)...")
    for i in range(warmup_runs):
        remover.remove_background(str(temp_path), return_bytes=False)
        if (i + 1) % 5 == 0:
            print(f"  Warmup progress: {i + 1}/{warmup_runs}")

    # Benchmark
    print(f"\nRunning benchmark ({num_runs} runs)...")
    latencies = []

    for i in range(num_runs):
        start = time.perf_counter()
        remover.remove_background(str(temp_path), return_bytes=False)
        latency = (time.perf_counter() - start) * 1000  # ms
        latencies.append(latency)

        if (i + 1) % 20 == 0:
            print(f"  Progress: {i + 1}/{num_runs}")

    # Statistics
    latencies_np = np.array(latencies)
    p50 = np.percentile(latencies_np, 50)
    p95 = np.percentile(latencies_np, 95)
    p99 = np.percentile(latencies_np, 99)
    mean = np.mean(latencies_np)
    std = np.std(latencies_np)
    min_lat = np.min(latencies_np)
    max_lat = np.max(latencies_np)

    # Results
    print(f"\n{'=' * 60}")
    print(f"BiRefNet Benchmark Results ({num_runs} runs)")
    print(f"{'=' * 60}")
    print(f"  Mean:    {mean:.2f}ms (±{std:.2f}ms)")
    print(f"  Min:     {min_lat:.2f}ms")
    print(f"  Max:     {max_lat:.2f}ms")
    print(f"  p50:     {p50:.2f}ms")
    print(f"  p95:     {p95:.2f}ms")
    print(f"  p99:     {p99:.2f}ms")
    print(f"{'=' * 60}")
    print(f"  Target:  ≤80ms (p95)")
    print(f"  Status:  {'✅ PASS' if p95 <= 80 else '❌ FAIL'} (p95={p95:.2f}ms)")
    print(f"{'=' * 60}")

    # Throughput
    throughput = 1000.0 / mean  # images/sec
    print(f"\nThroughput: {throughput:.2f} images/sec")

    # Cleanup
    temp_path.unlink()

    return {
        "mean": mean,
        "std": std,
        "p50": p50,
        "p95": p95,
        "p99": p99,
        "throughput": throughput,
        "pass": p95 <= 80
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Benchmark BiRefNet performance")
    parser.add_argument(
        "--model-dir",
        type=str,
        default="/home/ec2-user/video-message-app/video-message-app/data/models/birefnet-portrait",
        help="Path to BiRefNet model directory"
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=100,
        help="Number of benchmark runs"
    )
    parser.add_argument(
        "--warmup",
        type=int,
        default=10,
        help="Number of warmup runs"
    )

    args = parser.parse_args()

    try:
        results = benchmark(args.model_dir, args.runs, args.warmup)
        sys.exit(0 if results["pass"] else 1)
    except Exception as e:
        print(f"\n❌ Benchmark failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
