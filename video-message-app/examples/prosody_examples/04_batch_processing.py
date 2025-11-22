"""
Example 4: Batch Processing
============================

This example demonstrates how to process multiple audio files efficiently
with parallel processing and progress tracking.

Requirements:
- praat-parselmouth==0.4.3
- tqdm (for progress bar): pip install tqdm
"""

from pathlib import Path
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Tuple

try:
    from tqdm import tqdm
    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False
    print("⚠️ tqdm not available. Install with: pip install tqdm")

sys.path.append(str(Path(__file__).parent.parent.parent / "backend"))

from services.prosody_adjuster import ProsodyAdjuster, PARSELMOUTH_AVAILABLE


def process_single_file(
    audio_path: Path,
    text: str,
    preset: str = "celebration"
) -> Tuple[str, float, bool]:
    """
    Process a single audio file.

    Args:
        audio_path: Path to audio file
        text: Original text
        preset: Prosody preset

    Returns:
        (output_path, confidence, success)
    """
    presets = {
        "celebration": {"pitch_shift": 1.15, "tempo_shift": 1.10, "energy_shift": 1.20},
        "calm": {"pitch_shift": 0.95, "tempo_shift": 0.90, "energy_shift": 0.85},
        "professional": {"pitch_shift": 1.00, "tempo_shift": 0.95, "energy_shift": 1.10},
        "friendly": {"pitch_shift": 1.08, "tempo_shift": 1.00, "energy_shift": 1.10},
    }

    params = presets.get(preset, presets["celebration"])

    try:
        adjuster = ProsodyAdjuster(**params)
        adjusted_path, confidence, details = adjuster.apply(
            audio_path=str(audio_path),
            text=text
        )

        return adjusted_path, confidence, True

    except Exception as e:
        print(f"❌ Failed: {audio_path.name} - {e}")
        return "", 0.0, False


def batch_process_sequential(
    audio_files: List[Path],
    texts: List[str],
    preset: str = "celebration"
) -> List[Tuple[str, float, bool]]:
    """
    Process audio files sequentially (single-threaded).

    Args:
        audio_files: List of audio file paths
        texts: List of texts (corresponding to audio_files)
        preset: Prosody preset

    Returns:
        List of (output_path, confidence, success) tuples
    """
    results = []

    print(f"\nProcessing {len(audio_files)} files sequentially...")

    if TQDM_AVAILABLE:
        iterator = tqdm(zip(audio_files, texts), total=len(audio_files))
    else:
        iterator = zip(audio_files, texts)

    for audio_file, text in iterator:
        result = process_single_file(audio_file, text, preset)
        results.append(result)

    return results


def batch_process_parallel(
    audio_files: List[Path],
    texts: List[str],
    preset: str = "celebration",
    max_workers: int = 4
) -> List[Tuple[str, float, bool]]:
    """
    Process audio files in parallel (multi-threaded).

    Args:
        audio_files: List of audio file paths
        texts: List of texts (corresponding to audio_files)
        preset: Prosody preset
        max_workers: Maximum number of parallel workers

    Returns:
        List of (output_path, confidence, success) tuples
    """
    results = []

    print(f"\nProcessing {len(audio_files)} files in parallel (max_workers={max_workers})...")

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        futures = {
            executor.submit(process_single_file, audio_file, text, preset): (audio_file, text)
            for audio_file, text in zip(audio_files, texts)
        }

        # Process completed tasks with progress bar
        if TQDM_AVAILABLE:
            iterator = tqdm(as_completed(futures), total=len(futures))
        else:
            iterator = as_completed(futures)

        for future in iterator:
            result = future.result()
            results.append(result)

    return results


def main():
    """Main function."""

    print("Example 4: Batch Processing")
    print("="*50)

    if not PARSELMOUTH_AVAILABLE:
        print("❌ Parselmouth not available")
        return

    # Sample audio files (replace with your actual files)
    audio_directory = Path("audio_input")

    if not audio_directory.exists():
        print(f"❌ Directory not found: {audio_directory}")
        print("\nCreating sample directory structure...")
        audio_directory.mkdir(exist_ok=True)
        print("Please place your WAV files in:", audio_directory)
        return

    # Find all WAV files
    audio_files = list(audio_directory.glob("*.wav"))

    if not audio_files:
        print(f"❌ No WAV files found in {audio_directory}")
        return

    print(f"Found {len(audio_files)} audio files")

    # Generate texts (you can customize this)
    texts = [f.stem for f in audio_files]

    # Compare sequential vs parallel processing
    import time

    # Sequential processing
    print("\n" + "="*50)
    print("Sequential Processing")
    print("="*50)

    start_time = time.time()
    sequential_results = batch_process_sequential(audio_files, texts, preset="celebration")
    sequential_time = time.time() - start_time

    # Parallel processing
    print("\n" + "="*50)
    print("Parallel Processing")
    print("="*50)

    start_time = time.time()
    parallel_results = batch_process_parallel(audio_files, texts, preset="celebration", max_workers=4)
    parallel_time = time.time() - start_time

    # Summary
    print("\n" + "="*50)
    print("Summary")
    print("="*50)

    successful_sequential = sum(1 for _, _, success in sequential_results if success)
    successful_parallel = sum(1 for _, _, success in parallel_results if success)

    print(f"\nSequential:")
    print(f"  Total files: {len(audio_files)}")
    print(f"  Successful: {successful_sequential}")
    print(f"  Time: {sequential_time:.2f}s")

    print(f"\nParallel:")
    print(f"  Total files: {len(audio_files)}")
    print(f"  Successful: {successful_parallel}")
    print(f"  Time: {parallel_time:.2f}s")

    speedup = sequential_time / parallel_time if parallel_time > 0 else 1.0
    print(f"\nSpeedup: {speedup:.2f}x")

    # Average confidence scores
    avg_confidence_seq = sum(c for _, c, s in sequential_results if s) / max(successful_sequential, 1)
    avg_confidence_par = sum(c for _, c, s in parallel_results if s) / max(successful_parallel, 1)

    print(f"\nAverage Confidence:")
    print(f"  Sequential: {avg_confidence_seq:.2f}")
    print(f"  Parallel: {avg_confidence_par:.2f}")


if __name__ == "__main__":
    main()
