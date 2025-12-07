# Changelog

All notable changes to the Video Message App will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

#### Person Detection - Transparent Padding Control (#1)
- **UI Controls for Transparent Padding**
  - Added checkbox to enable/disable transparent padding (default: ON)
  - Added slider to adjust padding size from 0px to 500px (default: 300px)
  - Real-time padding size display next to slider

- **Frontend Components** (`frontend/src/components/PersonDetection.js`)
  - New state management for padding settings:
    - `transparentPaddingSize`: Configurable padding size (0-500px)
    - `addTransparentPadding`: Boolean toggle for padding feature
  - Enhanced UI with styled padding controls (`.padding-control` section)
  - Parameter propagation to extraction API

- **API Integration** (`frontend/src/services/api.js`)
  - Updated `extractSelectedPersons()` to accept new parameters:
    - `addTransparentPadding` (boolean)
    - `transparentPaddingSize` (integer)
  - Proper query parameter handling in API calls

**User Impact**: Users can now customize the transparent border around extracted persons, allowing better integration with video generation and D-ID processing.

---

#### Voice Quality Enhancement (#2)
- **VOICEVOX Intonation Control**
  - Added `intonation_scale` parameter (range: 0.0-2.0, default: 1.0)
  - Expressive speech control for more natural-sounding voices
  - Lower values (0.5) for flat/monotone speech
  - Higher values (1.5-2.0) for emotional/expressive speech

- **OpenVoice FFmpeg Post-Processing**
  - Added `pitch` parameter (range: -0.15 to +0.15)
    - Negative values: Lower pitch (deeper voice)
    - Positive values: Higher pitch (brighter voice)
  - Added `volume` parameter (range: 0.0 to 2.0)
    - 0.5: Quieter output
    - 1.0: Default volume
    - 2.0: Maximum amplification

- **Backend Service Integration**
  - **unified_voice_service.py** (L247-260)
    - Added `intonation` parameter to VOICEVOX synthesis
    - Pass-through of `pitch` and `volume` to OpenVoice

  - **openvoice_hybrid_client.py** (L95-143)
    - New function signature with `pitch`, `volume` parameters
    - FFmpeg post-processing pipeline integration

  - **openvoice_native_client.py** (HTTP API)
    - Updated `/voice-clone/synthesize` endpoint to accept new parameters

**User Impact**: Users can now fine-tune voice characteristics for both VOICEVOX and OpenVoice, resulting in more natural and customizable speech output.

---

### Technical Details

#### Modified Files Summary

**Issue #1 (Padding Control)**:
```
frontend/src/components/PersonDetection.js    (+22 lines)
frontend/src/components/PersonDetection.css   (+15 lines)
frontend/src/services/api.js                  (+2 parameters)
```

**Issue #2 (Voice Quality)**:
```
backend/services/unified_voice_service.py     (+3 parameters in L253-259)
backend/services/openvoice_hybrid_client.py   (+3 parameters in L95-130)
backend/services/openvoice_native_client.py   (+2 HTTP parameters)
```

---

## [Previous Releases]

### [1.0.0] - 2024-11-22
- Initial release with person detection and voice synthesis capabilities
- D-ID video generation integration
- VOICEVOX and OpenVoice V2 support
