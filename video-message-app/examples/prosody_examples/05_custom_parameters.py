"""
Example 5: Custom Parameters
=============================

This example demonstrates how to fine-tune prosody adjustments with custom
parameters tailored to specific needs.

Requirements:
- praat-parselmouth==0.4.3
"""

from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent.parent / "backend"))

from services.prosody_adjuster import ProsodyAdjuster, PARSELMOUTH_AVAILABLE


def calculate_dynamic_parameters(
    emotion: str,
    intensity: str = "moderate"
) -> dict:
    """
    Calculate prosody parameters based on emotion and intensity.

    Args:
        emotion: Target emotion (happy, sad, neutral, excited, calm)
        intensity: Adjustment intensity (mild, moderate, strong)

    Returns:
        Dictionary of prosody parameters
    """
    # Base emotion adjustments
    emotion_base = {
        "happy": {"pitch_shift": 1.10, "tempo_shift": 1.05, "energy_shift": 1.15},
        "excited": {"pitch_shift": 1.20, "tempo_shift": 1.12, "energy_shift": 1.25},
        "calm": {"pitch_shift": 0.98, "tempo_shift": 0.95, "energy_shift": 0.90},
        "sad": {"pitch_shift": 0.95, "tempo_shift": 0.90, "energy_shift": 0.85},
        "neutral": {"pitch_shift": 1.00, "tempo_shift": 1.00, "energy_shift": 1.00},
    }

    # Intensity multipliers
    intensity_multipliers = {
        "mild": 0.5,      # 50% of emotion adjustment
        "moderate": 1.0,  # 100% (default)
        "strong": 1.5     # 150%
    }

    base_params = emotion_base.get(emotion, emotion_base["neutral"])
    multiplier = intensity_multipliers.get(intensity, 1.0)

    # Calculate adjusted parameters
    params = {}

    for key, value in base_params.items():
        if key == "pitch_shift" or key == "tempo_shift" or key == "energy_shift":
            # Apply multiplier to deviation from 1.0
            deviation = (value - 1.0) * multiplier
            adjusted_value = 1.0 + deviation

            # Clamp to safe ranges
            if key == "pitch_shift":
                adjusted_value = max(0.90, min(1.25, adjusted_value))
            elif key == "tempo_shift":
                adjusted_value = max(0.95, min(1.15, adjusted_value))
            elif key == "energy_shift":
                adjusted_value = max(1.00, min(1.30, adjusted_value))

            params[key] = adjusted_value

    return params


def test_parameter_combinations():
    """Test various parameter combinations."""

    print("Example 5: Custom Parameters")
    print("="*50)

    if not PARSELMOUTH_AVAILABLE:
        print("❌ Parselmouth not available")
        return

    # Test cases
    test_cases = [
        {
            "name": "Mild happiness",
            "params": calculate_dynamic_parameters("happy", "mild"),
            "use_case": "Subtle positive tone for greetings"
        },
        {
            "name": "Strong excitement",
            "params": calculate_dynamic_parameters("excited", "strong"),
            "use_case": "Big announcements, celebrations"
        },
        {
            "name": "Moderate calm",
            "params": calculate_dynamic_parameters("calm", "moderate"),
            "use_case": "Meditation, relaxation guides"
        },
        {
            "name": "Mild sadness",
            "params": calculate_dynamic_parameters("sad", "mild"),
            "use_case": "Sympathy messages, condolences"
        },
        {
            "name": "Neutral (no adjustment)",
            "params": calculate_dynamic_parameters("neutral", "moderate"),
            "use_case": "Informational content"
        }
    ]

    # Display parameter combinations
    print("\nParameter Combinations:")
    print("-"*50)

    for i, test_case in enumerate(test_cases, 1):
        params = test_case["params"]

        print(f"\n{i}. {test_case['name']}")
        print(f"   Use case: {test_case['use_case']}")
        print(f"   Parameters:")
        print(f"     - Pitch: {params['pitch_shift']:.2f} ({(params['pitch_shift']-1)*100:+.0f}%)")
        print(f"     - Tempo: {params['tempo_shift']:.2f} ({(params['tempo_shift']-1)*100:+.0f}%)")
        print(f"     - Energy: {params['energy_shift']:.2f} ({(params['energy_shift']-1)*100:+.0f}%)")

    # Test audio file
    audio_path = "speech.wav"

    if not Path(audio_path).exists():
        print(f"\n❌ Audio file not found: {audio_path}")
        print("Create a sample audio file to test adjustments")
        return

    # Apply each parameter combination
    print("\n" + "="*50)
    print("Applying Adjustments")
    print("="*50)

    results = []

    for test_case in test_cases:
        name = test_case["name"]
        params = test_case["params"]

        print(f"\n{name}...")

        try:
            adjuster = ProsodyAdjuster(**params)

            adjusted_path, confidence, details = adjuster.apply(
                audio_path=audio_path,
                text=name
            )

            print(f"  ✅ Success")
            print(f"  Output: {adjusted_path}")
            print(f"  Confidence: {confidence:.2f}")

            results.append({
                "name": name,
                "path": adjusted_path,
                "confidence": confidence,
                "params": params
            })

        except Exception as e:
            print(f"  ❌ Error: {e}")

    # Summary
    print("\n" + "="*50)
    print("Summary")
    print("="*50)

    if results:
        # Sort by confidence
        sorted_results = sorted(results, key=lambda x: x["confidence"], reverse=True)

        print("\nResults sorted by confidence:")

        for i, result in enumerate(sorted_results, 1):
            print(f"\n{i}. {result['name']}")
            print(f"   Confidence: {result['confidence']:.2f}")
            print(f"   Output: {result['path']}")

        # Best and worst
        best = sorted_results[0]
        worst = sorted_results[-1]

        print(f"\n🏆 Best quality: {best['name']} (confidence: {best['confidence']:.2f})")
        print(f"⚠️ Lowest quality: {worst['name']} (confidence: {worst['confidence']:.2f})")

        # Recommendations
        print("\nRecommendations:")
        print("  - High confidence (>0.85): Safe for production")
        print("  - Medium confidence (0.70-0.85): Review manually")
        print("  - Low confidence (<0.70): Reduce adjustments")

    else:
        print("No results to display")


def ab_test_adjustments():
    """A/B test different adjustment levels."""

    print("\n" + "="*50)
    print("A/B Testing: Moderate vs Strong Adjustments")
    print("="*50)

    audio_path = "speech.wav"

    if not Path(audio_path).exists():
        print(f"❌ Audio file not found: {audio_path}")
        return

    # Test A: Moderate adjustments
    params_a = calculate_dynamic_parameters("happy", "moderate")
    print("\nTest A: Moderate adjustments")
    print(f"  Params: {params_a}")

    adjuster_a = ProsodyAdjuster(**params_a)
    adjusted_a, confidence_a, _ = adjuster_a.apply(audio_path, "Test A")

    print(f"  Output: {adjusted_a}")
    print(f"  Confidence: {confidence_a:.2f}")

    # Test B: Strong adjustments
    params_b = calculate_dynamic_parameters("happy", "strong")
    print("\nTest B: Strong adjustments")
    print(f"  Params: {params_b}")

    adjuster_b = ProsodyAdjuster(**params_b)
    adjusted_b, confidence_b, _ = adjuster_b.apply(audio_path, "Test B")

    print(f"  Output: {adjusted_b}")
    print(f"  Confidence: {confidence_b:.2f}")

    # Compare
    print("\n" + "-"*50)
    print("Comparison:")

    if confidence_a > confidence_b:
        print(f"  ✅ Test A wins (confidence: {confidence_a:.2f} vs {confidence_b:.2f})")
        print("  Recommendation: Use moderate adjustments")
    else:
        print(f"  ✅ Test B wins (confidence: {confidence_b:.2f} vs {confidence_a:.2f})")
        print("  Recommendation: Strong adjustments are acceptable")


if __name__ == "__main__":
    test_parameter_combinations()
    # ab_test_adjustments()  # Uncomment to run A/B test
