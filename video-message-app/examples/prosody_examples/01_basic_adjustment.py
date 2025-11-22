"""
Example 1: Basic Prosody Adjustment
====================================

This example demonstrates the simplest way to use Prosody adjustment
with default parameters.

Requirements:
- praat-parselmouth==0.4.3
- numpy>=1.24.0
"""

from pathlib import Path
import sys

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent / "backend"))

from services.prosody_adjuster import ProsodyAdjuster, PARSELMOUTH_AVAILABLE


def basic_adjustment():
    """Apply basic prosody adjustment with default parameters."""

    # Check if Parselmouth is available
    if not PARSELMOUTH_AVAILABLE:
        print("❌ Parselmouth not available")
        print("Install with: pip install praat-parselmouth==0.4.3")
        return

    print("Example 1: Basic Prosody Adjustment")
    print("="*50)

    # Input audio file
    audio_path = "speech.wav"  # Replace with your audio file
    text = "Happy Birthday!"

    # Check if file exists
    if not Path(audio_path).exists():
        print(f"❌ Audio file not found: {audio_path}")
        print("Please provide a valid WAV file")
        return

    # Create ProsodyAdjuster with default parameters
    # - pitch_shift: 1.15 (+15% higher pitch)
    # - tempo_shift: 1.10 (+10% faster)
    # - energy_shift: 1.20 (+20% louder)
    adjuster = ProsodyAdjuster()

    print("\nAdjustment Parameters:")
    print(f"  Pitch shift: {adjuster.pitch_shift:.2f} (+{(adjuster.pitch_shift-1)*100:.0f}%)")
    print(f"  Tempo shift: {adjuster.tempo_shift:.2f} (+{(adjuster.tempo_shift-1)*100:.0f}%)")
    print(f"  Energy shift: {adjuster.energy_shift:.2f} (+{(adjuster.energy_shift-1)*100:.0f}%)")

    # Apply adjustments
    print("\nProcessing...")

    try:
        adjusted_path, confidence, details = adjuster.apply(
            audio_path=audio_path,
            text=text
        )

        # Display results
        print("\n✅ Success!")
        print(f"\nOutput file: {adjusted_path}")
        print(f"Confidence score: {confidence:.2f}")

        print("\nQuality Checks:")
        for check, result in details.items():
            if check == "final_confidence":
                continue

            status = "✅" if result == "PASS" else "⚠️"
            print(f"  {status} {check}: {result}")

        # Interpret confidence score
        print("\nConfidence Interpretation:")
        if confidence >= 0.90:
            print("  ✅ Excellent - Natural-sounding adjustments")
        elif confidence >= 0.70:
            print("  ✅ Good - Acceptable quality")
        elif confidence >= 0.50:
            print("  ⚠️ Fair - Some artifacts may be present")
        else:
            print("  ❌ Poor - Consider reducing adjustments")

    except Exception as e:
        print(f"\n❌ Error: {e}")


if __name__ == "__main__":
    basic_adjustment()
