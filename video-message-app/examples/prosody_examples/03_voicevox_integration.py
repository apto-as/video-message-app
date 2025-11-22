"""
Example 3: VOICEVOX Integration
================================

This example demonstrates how to integrate Prosody adjustment with VOICEVOX
text-to-speech synthesis.

Flow:
1. Synthesize speech with VOICEVOX
2. Apply prosody adjustments
3. Save enhanced audio

Requirements:
- VOICEVOX engine running on port 50021
- praat-parselmouth==0.4.3
- requests
"""

from pathlib import Path
import sys
import tempfile

import requests

sys.path.append(str(Path(__file__).parent.parent.parent / "backend"))

from services.prosody_adjuster import ProsodyAdjuster, PARSELMOUTH_AVAILABLE


def synthesize_voicevox(text: str, speaker: int = 3) -> bytes:
    """
    Synthesize speech with VOICEVOX.

    Args:
        text: Text to synthesize
        speaker: VOICEVOX speaker ID (3 = ずんだもん)

    Returns:
        Audio bytes (WAV format)
    """
    base_url = "http://localhost:50021"

    # Step 1: Create audio query
    response = requests.post(
        f"{base_url}/audio_query",
        params={"text": text, "speaker": speaker}
    )

    if response.status_code != 200:
        raise RuntimeError(f"VOICEVOX audio_query failed: {response.status_code}")

    audio_query = response.json()

    # Step 2: Synthesize
    response = requests.post(
        f"{base_url}/synthesis",
        params={"speaker": speaker},
        json=audio_query
    )

    if response.status_code != 200:
        raise RuntimeError(f"VOICEVOX synthesis failed: {response.status_code}")

    return response.content


def voicevox_with_prosody(text: str, speaker: int = 3, preset: str = "friendly") -> str:
    """
    Synthesize speech with VOICEVOX and apply prosody adjustments.

    Args:
        text: Text to synthesize
        speaker: VOICEVOX speaker ID
        preset: Prosody preset name

    Returns:
        Path to adjusted audio file
    """
    if not PARSELMOUTH_AVAILABLE:
        raise RuntimeError("Parselmouth not available")

    print(f"Text: {text}")
    print(f"Speaker: {speaker}")
    print(f"Preset: {preset}")

    # Step 1: Synthesize with VOICEVOX
    print("\n[1/3] Synthesizing with VOICEVOX...")

    try:
        audio_data = synthesize_voicevox(text, speaker)
    except Exception as e:
        raise RuntimeError(f"VOICEVOX synthesis failed: {e}")

    # Save VOICEVOX output
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
        temp_file.write(audio_data)
        voicevox_audio_path = temp_file.name

    print(f"✅ VOICEVOX audio: {voicevox_audio_path}")

    # Step 2: Apply prosody adjustments
    print("\n[2/3] Applying prosody adjustments...")

    # Get preset parameters
    presets = {
        "celebration": {"pitch_shift": 1.15, "tempo_shift": 1.10, "energy_shift": 1.20},
        "calm": {"pitch_shift": 0.95, "tempo_shift": 0.90, "energy_shift": 0.85},
        "professional": {"pitch_shift": 1.00, "tempo_shift": 0.95, "energy_shift": 1.10},
        "friendly": {"pitch_shift": 1.08, "tempo_shift": 1.00, "energy_shift": 1.10},
    }

    params = presets.get(preset, presets["friendly"])
    adjuster = ProsodyAdjuster(**params)

    try:
        adjusted_path, confidence, details = adjuster.apply(
            audio_path=voicevox_audio_path,
            text=text
        )
    except Exception as e:
        raise RuntimeError(f"Prosody adjustment failed: {e}")

    print(f"✅ Adjusted audio: {adjusted_path}")
    print(f"   Confidence: {confidence:.2f}")

    # Step 3: Cleanup temporary file
    Path(voicevox_audio_path).unlink()

    return adjusted_path


def main():
    """Main function."""

    print("Example 3: VOICEVOX + Prosody Integration")
    print("="*50)

    # Check VOICEVOX availability
    try:
        response = requests.get("http://localhost:50021/version")
        voicevox_version = response.json()["version"]
        print(f"\n✅ VOICEVOX version: {voicevox_version}")
    except Exception as e:
        print(f"\n❌ VOICEVOX not available: {e}")
        print("Start VOICEVOX with: docker-compose up -d voicevox")
        return

    # Example texts
    examples = [
        ("お誕生日おめでとうございます！", 3, "celebration"),
        ("ご清聴ありがとうございました。", 2, "professional"),
        ("ゆっくり休んでくださいね。", 1, "calm"),
        ("こんにちは！お会いできて嬉しいです。", 3, "friendly"),
    ]

    # Process each example
    results = []

    for text, speaker, preset in examples:
        print(f"\n{'-'*50}")
        try:
            adjusted_path = voicevox_with_prosody(text, speaker, preset)
            results.append((text, adjusted_path))
        except Exception as e:
            print(f"❌ Error: {e}")

    # Summary
    print(f"\n{'='*50}")
    print("Summary")
    print(f"{'='*50}")

    for text, path in results:
        print(f"  {text[:20]}... → {path}")

    print("\nAll adjusted audio files are ready to use!")


if __name__ == "__main__":
    main()
