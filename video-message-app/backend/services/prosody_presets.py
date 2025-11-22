"""
Prosody Preset Management
Author: Hera (Strategic Commander)
Date: 2025-11-07

Purpose: Manage prosody adjustment presets for different voice styles.
"""

from dataclasses import dataclass
from typing import List, Optional
from enum import Enum


class PresetCategory(str, Enum):
    """Preset category for UI grouping."""
    CELEBRATION = "celebration"  # 祝福・祝賀
    MOTIVATION = "motivation"    # 励まし・応援
    EMOTION = "emotion"          # 感情表現
    CUSTOM = "custom"            # カスタム


@dataclass
class ProsodyPreset:
    """Prosody adjustment preset configuration."""

    name: str
    display_name: str
    category: PresetCategory
    pitch_shift: float
    tempo_shift: float
    energy_shift: float
    description: str
    icon: str

    def __post_init__(self):
        """Validate parameters."""
        if not 0.90 <= self.pitch_shift <= 1.25:
            raise ValueError(
                f"pitch_shift must be in [0.90, 1.25], got {self.pitch_shift}"
            )

        if not 0.95 <= self.tempo_shift <= 1.15:
            raise ValueError(
                f"tempo_shift must be in [0.95, 1.15], got {self.tempo_shift}"
            )

        if not 1.00 <= self.energy_shift <= 1.30:
            raise ValueError(
                f"energy_shift must be in [1.00, 1.30], got {self.energy_shift}"
            )


# Built-in Presets
BUILTIN_PRESETS = [
    ProsodyPreset(
        name="celebration",
        display_name="お祝い 🎊",
        category=PresetCategory.CELEBRATION,
        pitch_shift=1.15,
        tempo_shift=1.10,
        energy_shift=1.20,
        description="誕生日、記念日、卒業式などのお祝いメッセージに最適",
        icon="🎉"
    ),
    ProsodyPreset(
        name="energetic",
        display_name="元気いっぱい ⚡",
        category=PresetCategory.MOTIVATION,
        pitch_shift=1.10,
        tempo_shift=1.15,
        energy_shift=1.25,
        description="スポーツ、応援、励ましメッセージに最適",
        icon="💪"
    ),
    ProsodyPreset(
        name="joyful",
        display_name="やさしい喜び 😊",
        category=PresetCategory.EMOTION,
        pitch_shift=1.20,
        tempo_shift=1.05,
        energy_shift=1.15,
        description="感謝、お礼、優しい挨拶メッセージに最適",
        icon="🌸"
    ),
    ProsodyPreset(
        name="neutral",
        display_name="ナチュラル ➖",
        category=PresetCategory.CUSTOM,
        pitch_shift=1.00,
        tempo_shift=1.00,
        energy_shift=1.00,
        description="調整なし（通常の音声）",
        icon="📢"
    ),
]


def list_presets(category: Optional[PresetCategory] = None) -> List[ProsodyPreset]:
    """
    List all available presets, optionally filtered by category.

    Args:
        category: Optional category filter

    Returns:
        List of ProsodyPreset objects
    """
    presets = BUILTIN_PRESETS

    if category:
        presets = [p for p in presets if p.category == category]

    return presets


def get_preset_by_name(name: str) -> ProsodyPreset:
    """
    Get preset by name.

    Args:
        name: Preset name (e.g., "celebration")

    Returns:
        ProsodyPreset object

    Raises:
        ValueError: If preset not found
    """
    for preset in BUILTIN_PRESETS:
        if preset.name == name:
            return preset

    raise ValueError(
        f"Preset not found: {name}. "
        f"Available: {[p.name for p in BUILTIN_PRESETS]}"
    )


def get_default_preset() -> ProsodyPreset:
    """
    Get default preset (celebration).

    Returns:
        Default ProsodyPreset object
    """
    return get_preset_by_name("celebration")


def select_preset_for_text(text: str) -> str:
    """
    Auto-select preset based on text content (optional feature).

    Args:
        text: Input text

    Returns:
        Preset name (str)

    Example:
        >>> select_preset_for_text("Happy Birthday!")
        'celebration'
        >>> select_preset_for_text("You can do it!")
        'energetic'
    """

    # Keywords detection
    celebration_keywords = [
        "誕生日", "記念日", "卒業", "おめでとう",
        "happy", "congratulations", "anniversary", "graduation"
    ]

    energetic_keywords = [
        "頑張", "応援", "ファイト", "できる",
        "go", "fight", "cheer", "motivation"
    ]

    joyful_keywords = [
        "ありがとう", "感謝", "嬉しい",
        "thank", "grateful", "appreciate"
    ]

    text_lower = text.lower()

    # Check keywords
    if any(kw in text_lower for kw in celebration_keywords):
        return "celebration"
    elif any(kw in text_lower for kw in energetic_keywords):
        return "energetic"
    elif any(kw in text_lower for kw in joyful_keywords):
        return "joyful"
    else:
        return "celebration"  # Default
