"""
Example 2: Using Presets
=========================

This example demonstrates how to use predefined presets for common use cases.

Presets:
- celebration: Joyful and energetic (birthdays, congratulations)
- calm: Relaxed and gentle (meditation, comfort)
- professional: Clear and authoritative (business, presentations)
- dramatic: Emphatic with pauses (storytelling, narration)
- friendly: Warm and approachable (greetings, introductions)

Requirements:
- praat-parselmouth==0.4.3
"""

from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent.parent / "backend"))

from services.prosody_adjuster import ProsodyAdjuster, PARSELMOUTH_AVAILABLE


# Preset configurations
PRESETS = {
    "celebration": {
        "pitch_shift": 1.15,
        "tempo_shift": 1.10,
        "energy_shift": 1.20,
        "description": "Joyful and energetic for birthdays, congratulations"
    },
    "calm": {
        "pitch_shift": 0.95,
        "tempo_shift": 0.90,
        "energy_shift": 0.85,
        "description": "Relaxed and gentle for meditation, comfort"
    },
    "professional": {
        "pitch_shift": 1.00,
        "tempo_shift": 0.95,
        "energy_shift": 1.10,
        "description": "Clear and authoritative for business announcements"
    },
    "dramatic": {
        "pitch_shift": 1.10,
        "tempo_shift": 0.95,
        "energy_shift": 1.25,
        "description": "Emphatic for storytelling, narration"
    },
    "friendly": {
        "pitch_shift": 1.08,
        "tempo_shift": 1.00,
        "energy_shift": 1.10,
        "description": "Warm and approachable for greetings"
    }
}


def get_adjuster_from_preset(preset_name: str) -> ProsodyAdjuster:
    """Get ProsodyAdjuster configured with preset parameters."""
    if preset_name not in PRESETS:
        raise ValueError(f"Unknown preset: {preset_name}")

    params = PRESETS[preset_name]

    return ProsodyAdjuster(
        pitch_shift=params["pitch_shift"],
        tempo_shift=params["tempo_shift"],
        energy_shift=params["energy_shift"]
    )


def apply_preset(audio_path: str, text: str, preset: str):
    """Apply preset to audio file."""

    if not PARSELMOUTH_AVAILABLE:
        print("❌ Parselmouth not available")
        return

    if not Path(audio_path).exists():
        print(f"❌ Audio file not found: {audio_path}")
        return

    print(f"\nApplying preset: {preset}")
    print(f"Description: {PRESETS[preset]['description']}")

    # Get adjuster with preset
    adjuster = get_adjuster_from_preset(preset)

    print("\nParameters:")
    print(f"  Pitch: {adjuster.pitch_shift:.2f} ({(adjuster.pitch_shift-1)*100:+.0f}%)")
    print(f"  Tempo: {adjuster.tempo_shift:.2f} ({(adjuster.tempo_shift-1)*100:+.0f}%)")
    print(f"  Energy: {adjuster.energy_shift:.2f} ({(adjuster.energy_shift-1)*100:+.0f}%)")

    print("\nProcessing...")

    try:
        # Apply adjustments
        adjusted_path, confidence, details = adjuster.apply(
            audio_path=audio_path,
            text=text
        )

        # Display results
        print(f"\n✅ Success!")
        print(f"Output: {adjusted_path}")
        print(f"Confidence: {confidence:.2f}")

        return adjusted_path

    except Exception as e:
        print(f"\n❌ Error: {e}")
        return None


def compare_presets():
    """Compare multiple presets on the same audio."""

    print("Example 2: Comparing Presets")
    print("="*50)

    # Input audio
    audio_path = "speech.wav"  # Replace with your audio file
    text = "Welcome to our service!"

    if not Path(audio_path).exists():
        print(f"❌ Audio file not found: {audio_path}")
        print("Please provide a valid WAV file")
        return

    # Test all presets
    results = {}

    for preset_name in PRESETS:
        print(f"\n{'-'*50}")
        result = apply_preset(audio_path, text, preset_name)
        if result:
            results[preset_name] = result

    # Summary
    print(f"\n{'='*50}")
    print("Summary")
    print(f"{'='*50}")

    for preset_name, output_path in results.items():
        print(f"  {preset_name}: {output_path}")

    print("\nRecommendations:")
    print("  - Birthday messages → celebration")
    print("  - Business announcements → professional")
    print("  - Meditation guides → calm")
    print("  - Storytelling → dramatic")
    print("  - Greetings → friendly")


if __name__ == "__main__":
    compare_presets()
