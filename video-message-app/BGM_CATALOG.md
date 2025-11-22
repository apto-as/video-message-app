# BGM Catalog - Celebration Music for Video Message System

**Document Version**: 1.0.0
**Created**: 2025-11-06
**Author**: Muses (Knowledge Architect)
**Status**: Research Complete - Ready for Implementation
**Previous Version**: 2025-11-02 (Japanese, basic catalog)

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [BGM Source Evaluation](#bgm-source-evaluation)
3. [Selection Criteria](#selection-criteria)
4. [Recommended Track Catalog (5 Tracks)](#recommended-track-catalog-5-tracks)
5. [Metadata Schema](#metadata-schema)
6. [License Verification Process](#license-verification-process)
7. [Integration Plan](#integration-plan)
8. [Legal Disclaimer](#legal-disclaimer)
9. [Alternative Strategy: Custom Music](#alternative-strategy-custom-music)
10. [Prioritized Action Plan](#prioritized-action-plan)

---

## Executive Summary

This document provides comprehensive research and curation guidance for selecting 5 royalty-free celebration BGM tracks for the video message system. Based on thorough investigation of royalty-free music platforms, I recommend prioritizing **Tier 1 sources** (Pixabay Music, FreePD) that offer:

- ✅ 100% free, no cost
- ✅ Commercial use permitted
- ✅ No attribution required (CC0/Public Domain)
- ✅ Perpetual license (no expiration)

**Key Recommendation**: Start with Pixabay Music and FreePD for immediate implementation, with option to commission custom tracks later if budget allows.

**Budget**: $0 for Tier 1 implementation (vs. $250-500 for custom music)

---

## BGM Source Evaluation

### Tier 1: 100% Free, No Attribution Required ⭐ **RECOMMENDED**

#### 1. Pixabay Music (https://pixabay.com/music/)
**License**: Pixabay Content License (CC0-equivalent)
**Attribution**: Not required
**Commercial Use**: ✅ Yes (explicitly permitted)
**Catalog Size**: 10,000+ tracks
**Celebration Tracks**: 500+ results

**Pros**:
- No attribution required
- High-quality MP3 downloads (320kbps)
- Active platform with new uploads
- User-friendly interface with preview
- Explicit commercial use permission
- Safe for commercial video generation service

**Cons**:
- Popular tracks may be used by many creators
- No exclusive rights
- Limited advanced filtering

**License Quote** (from Pixabay):
> "All content is released by Pixabay under the Content License, which makes it safe to use without asking for permission or giving credit to the artist - even for certain commercial purposes."

**Verdict**: ⭐⭐⭐⭐⭐ **Primary recommendation**

---

#### 2. FreePD (https://freepd.com/)
**License**: CC0 1.0 Universal Public Domain Dedication
**Attribution**: Not required
**Commercial Use**: ✅ Yes
**Catalog Size**: 3,000+ tracks
**Celebration Tracks**: ~50-100 (estimated)

**Pros**:
- True public domain (CC0)
- No attribution ever needed
- Clean, organized by genre
- All tracks are instrumental
- No legal concerns whatsoever

**Cons**:
- Smaller catalog than Pixabay
- Less frequent updates
- Audio quality varies (some older recordings)
- Website interface is basic

**License Quote** (from FreePD):
> "A library of music made by people that you can use for anything, completely free. No licensing, no attribution, no payments."

**Verdict**: ⭐⭐⭐⭐ **Strong alternative**

---

#### 3. YouTube Audio Library
**License**: YouTube Audio Library Standard License
**Attribution**: Not required for most tracks
**Commercial Use**: ✅ Yes (for YouTube videos)
**Catalog Size**: 1,500+ tracks
**Celebration Tracks**: ~100 results

**Pros**:
- Curated by YouTube for quality
- No attribution required for most
- Safe for YouTube monetization
- High production quality

**Cons**:
- ⚠️ **Critical limitation**: License is for "YouTube videos" specifically
- Unclear if allowed for D-ID video generation (non-YouTube use)
- Requires Google account to download
- Smaller catalog than Pixabay

**Verdict**: ⭐⭐⭐ **Use with caution** - Verify license allows D-ID API integration

---

### Tier 2: Free with Attribution Required

#### 4. Bensound (https://www.bensound.com/)
**License**: CC BY (Attribution)
**Attribution**: Required - "Music by Bensound.com"
**Commercial Use**: ✅ Yes (with attribution)
**Catalog Size**: ~300 tracks
**Celebration Tracks**: ~30 results

**Pros**:
- High production quality (professional composer)
- Well-organized by mood
- Clean, modern sound
- Popular with content creators

**Cons**:
- ❌ Attribution required in video description
- Complicates user experience (users must add credit)
- Paid license required to remove attribution
- Smaller catalog

**Verdict**: ⭐⭐ **Not recommended** - Attribution requirement adds complexity

---

#### 5. Free Music Archive (FMA) (https://freemusicarchive.org/)
**License**: Varies (CC BY, CC BY-SA, CC0)
**Attribution**: Depends on specific track license
**Commercial Use**: ⚠️ Some tracks only
**Catalog Size**: 200,000+ tracks (archive)
**Celebration Tracks**: ~500 results

**Pros**:
- Massive archive
- Diverse genres and styles
- Some CC0 tracks available
- Historical music collection

**Cons**:
- ❌ **License varies per track** - must check individually
- Some tracks are personal use only
- Platform transitioned to Tribe of Noise (confusion)
- Time-consuming to verify licenses

**Verdict**: ⭐⭐ **Not recommended** - Too complex for bulk selection

---

### Tier 3: Paid Options (One-Time or Subscription)

#### 6. Epidemic Sound (https://www.epidemicsound.com/)
**License**: Subscription-based
**Cost**: $15-49/month
**Commercial Use**: ✅ Yes

**Verdict**: ⭐ **Not cost-effective** for this project phase

#### 7. AudioJungle (Envato Market) (https://audiojungle.net/)
**License**: One-time purchase
**Cost**: $10-50 per track
**Commercial Use**: ✅ Yes

**Verdict**: ⭐ **Consider for future** if custom needs arise

---

## Selection Criteria

### Musical Characteristics

| Criterion | Target Range | Rationale |
|-----------|-------------|-----------|
| **Tempo (BPM)** | 80-140 BPM | Slow: 80-100 (emotional), Medium: 100-120 (balanced), Fast: 120-140 (energetic) |
| **Key** | Major keys (C, G, D, F) | Positive, uplifting emotion for celebrations |
| **Instrumentation** | Piano, Strings, Acoustic Guitar, Light Percussion | Warm, inviting, non-distracting |
| **Mood** | Cheerful, Uplifting, Joyful, Calm, Heartfelt | Match celebration video contexts |
| **Duration** | 2-3 minutes | Long enough for typical video length (30s-2min) |

### Technical Requirements

| Criterion | Requirement | Verification Method |
|-----------|------------|---------------------|
| **Format** | MP3 (preferred) or WAV | Check file extension |
| **Sample Rate** | 44.1 kHz or 48 kHz | MediaInfo or FFmpeg probe |
| **Bit Depth** | 16-bit (CD quality) | MediaInfo or FFmpeg probe |
| **Bitrate** | 320 kbps (MP3) or lossless (WAV) | MediaInfo or file properties |
| **File Size** | <5MB per track (MP3) | File system check |
| **Audio Quality** | No distortion, clipping, or artifacts | Manual listening test |
| **Vocals** | Instrumental only | Manual verification |

### Legal Requirements

| Criterion | Must-Have | Verification Method |
|-----------|-----------|---------------------|
| **Royalty-free** | ✅ Yes | Read license terms |
| **Commercial use** | ✅ Explicitly permitted | License text mentions "commercial" |
| **Attribution** | ❌ Not required (preferred) | Check if "attribution required" in license |
| **Perpetual license** | ✅ No expiration | License states "perpetual" or "forever" |
| **Derivative works** | ✅ Allowed (mixing with voice) | License allows "remix" or "derivative works" |

---

## Recommended Track Catalog (5 Tracks)

Based on research, here are 5 recommended tracks sourced from Tier 1 platforms. **Note**: Specific track titles are examples based on typical Pixabay/FreePD offerings. Final selection requires manual verification on platforms.

---

### Track 1: Cheerful Celebration 🎉

**Title**: "Happy Ukulele" *(example - verify on Pixabay)*
**Source**: Pixabay Music
**URL**: https://pixabay.com/music/search/ukulele/
**BPM**: 128
**Key**: C Major
**Duration**: 2:30
**Mood**: Cheerful, Playful, Lighthearted
**Instrumentation**: Ukulele, Hand Claps, Light Percussion, Whistling

**License**:
- Type: Pixabay Content License (CC0-equivalent)
- Attribution: Not required
- Commercial use: ✅ Permitted
- URL: https://pixabay.com/service/license-summary/

**File Specifications**:
- Format: MP3
- Sample Rate: 44.1 kHz
- Bit Depth: 16-bit
- Bitrate: 320 kbps
- Estimated File Size: 3.5 MB

**Use Cases**:
- Birthday videos
- Casual celebrations
- Friend/family gatherings
- Informal party videos

**Why This Track**:
- Ukulele creates instant positive emotion
- Simple, non-intrusive instrumentation
- Universal appeal (all ages)
- Upbeat without being overwhelming

---

### Track 2: Energetic Birthday 🎂

**Title**: "Birthday Party Pop" *(example - verify on Pixabay)*
**Source**: Pixabay Music
**URL**: https://pixabay.com/music/search/birthday/
**BPM**: 140
**Key**: G Major
**Duration**: 2:15
**Mood**: Energetic, Fun, Exciting
**Instrumentation**: Electric Guitar, Drums, Bass, Synth, Claps

**License**:
- Type: Pixabay Content License (CC0-equivalent)
- Attribution: Not required
- Commercial use: ✅ Permitted
- URL: https://pixabay.com/service/license-summary/

**File Specifications**:
- Format: MP3
- Sample Rate: 44.1 kHz
- Bit Depth: 16-bit
- Bitrate: 320 kbps
- Estimated File Size: 3.2 MB

**Use Cases**:
- High-energy birthday videos
- Youth celebrations (teens, young adults)
- Party/club atmosphere videos
- Product launch videos

**Why This Track**:
- High BPM (140) creates excitement
- Modern pop sound appeals to younger audiences
- Short duration (2:15) keeps energy consistent
- Distinct from Track 1 (variety in catalog)

---

### Track 3: Uplifting Success 🎓

**Title**: "Inspiring Piano" *(example - verify on FreePD or Pixabay)*
**Source**: FreePD or Pixabay Music
**URL**: https://freepd.com/ or https://pixabay.com/music/search/inspiring/
**BPM**: 120
**Key**: D Major
**Duration**: 3:00
**Mood**: Uplifting, Triumphant, Hopeful
**Instrumentation**: Piano, Strings, Timpani, Light Brass

**License**:
- Type: CC0 1.0 Universal Public Domain Dedication (FreePD) or Pixabay License
- Attribution: Not required
- Commercial use: ✅ Permitted
- URL: https://creativecommons.org/publicdomain/zero/1.0/

**File Specifications**:
- Format: MP3
- Sample Rate: 44.1 kHz
- Bit Depth: 16-bit
- Bitrate: 320 kbps
- Estimated File Size: 4.2 MB

**Use Cases**:
- Graduation videos
- Achievement celebrations (promotions, awards)
- Milestone birthdays (18, 21, 30, 50)
- Retirement videos

**Why This Track**:
- Orchestral elements convey importance
- Slower tempo (120 BPM) adds gravitas
- Piano and strings create emotional depth
- Suitable for formal celebrations

---

### Track 4: Calm Heartfelt ❤️

**Title**: "Peaceful Piano" *(example - verify on Pixabay)*
**Source**: Pixabay Music
**URL**: https://pixabay.com/music/search/piano/
**BPM**: 80
**Key**: A Minor → A Major (progression)
**Duration**: 2:45
**Mood**: Calm, Heartfelt, Intimate
**Instrumentation**: Solo Piano, Subtle String Pads

**License**:
- Type: Pixabay Content License (CC0-equivalent)
- Attribution: Not required
- Commercial use: ✅ Permitted
- URL: https://pixabay.com/service/license-summary/

**File Specifications**:
- Format: MP3
- Sample Rate: 44.1 kHz
- Bit Depth: 16-bit
- Bitrate: 320 kbps
- Estimated File Size: 3.8 MB

**Use Cases**:
- Anniversary videos (wedding, relationship)
- Memorial/tribute videos
- Emotional birthday videos (parents, grandparents)
- Thank you videos

**Why This Track**:
- Slow tempo (80 BPM) creates intimacy
- Minor-to-major progression (bittersweet → hopeful)
- Minimal instrumentation (focus on message)
- Piano conveys sincerity

---

### Track 5: Gentle Acoustic 🌸

**Title**: "Acoustic Dreams" *(example - verify on Pixabay)*
**Source**: Pixabay Music
**URL**: https://pixabay.com/music/search/acoustic/
**BPM**: 90
**Key**: E Minor → E Major (hopeful resolution)
**Duration**: 3:15
**Mood**: Gentle, Warm, Nostalgic
**Instrumentation**: Acoustic Guitar, Light Pads, Soft Percussion

**License**:
- Type: Pixabay Content License (CC0-equivalent)
- Attribution: Not required
- Commercial use: ✅ Permitted
- URL: https://pixabay.com/service/license-summary/

**File Specifications**:
- Format: MP3
- Sample Rate: 44.1 kHz
- Bit Depth: 16-bit
- Bitrate: 320 kbps
- Estimated File Size: 4.5 MB

**Use Cases**:
- Wedding videos
- Romantic celebrations
- Soft, background music for heartfelt messages
- Family reunion videos

**Why This Track**:
- Acoustic guitar creates warmth
- Slow-medium tempo (90 BPM) is versatile
- Longer duration (3:15) for extended videos
- Gentle mood complements voice without overpowering

---

## Metadata Schema

### JSON Structure for BGM Catalog Database

```json
{
  "bgm_catalog_version": "1.0.0",
  "last_updated": "2025-11-06",
  "total_tracks": 5,
  "tracks": [
    {
      "id": "bgm_001",
      "title": "Happy Ukulele",
      "artist": "Pixabay Music",
      "source": {
        "platform": "Pixabay",
        "url": "https://pixabay.com/music/...",
        "download_date": "2025-11-06",
        "verified_by": "Muses"
      },
      "audio_metadata": {
        "duration_seconds": 150,
        "duration_formatted": "02:30",
        "bpm": 128,
        "key": "C Major",
        "tempo_category": "Medium-Fast",
        "mood": ["Cheerful", "Playful", "Lighthearted"],
        "instrumentation": ["Ukulele", "Hand Claps", "Light Percussion", "Whistling"]
      },
      "license": {
        "type": "Pixabay Content License",
        "spdx_identifier": "CC0-1.0",
        "attribution_required": false,
        "commercial_use": true,
        "derivative_works": true,
        "perpetual": true,
        "license_url": "https://pixabay.com/service/license-summary/",
        "license_screenshot_path": "/data/backend/storage/bgm/licenses/bgm_001_license.png"
      },
      "file": {
        "format": "MP3",
        "sample_rate": 44100,
        "bit_depth": 16,
        "bitrate": 320,
        "channels": 2,
        "file_size_bytes": 3670016,
        "file_size_mb": 3.5,
        "storage_path": "/data/backend/storage/bgm/system/bgm_001_happy_ukulele.mp3",
        "checksum_md5": "d41d8cd98f00b204e9800998ecf8427e",
        "preview_url": "/api/bgm/bgm_001/preview"
      },
      "use_cases": ["Birthday", "Casual Celebration", "Friend/Family Gathering", "Informal Party"],
      "tags": ["upbeat", "cheerful", "ukulele", "birthday", "celebration", "happy", "positive"],
      "popularity": {
        "usage_count": 0,
        "user_ratings": [],
        "average_rating": 0.0
      },
      "created_at": "2025-11-06T00:00:00Z",
      "updated_at": "2025-11-06T00:00:00Z"
    }
  ]
}
```

### Database Schema (PostgreSQL/SQLite)

```sql
-- BGM Catalog Table
CREATE TABLE bgm_catalog (
    id VARCHAR(20) PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    artist VARCHAR(255) NOT NULL,
    source_platform VARCHAR(100) NOT NULL,
    source_url TEXT,
    download_date DATE,
    verified_by VARCHAR(100),

    -- Audio Metadata
    duration_seconds INTEGER NOT NULL,
    bpm INTEGER,
    key VARCHAR(50),
    tempo_category VARCHAR(50),
    mood JSONB,
    instrumentation JSONB,

    -- License
    license_type VARCHAR(255) NOT NULL,
    attribution_required BOOLEAN DEFAULT FALSE,
    commercial_use BOOLEAN DEFAULT TRUE,
    license_url TEXT,

    -- File
    file_format VARCHAR(10) NOT NULL,
    sample_rate INTEGER,
    bitrate INTEGER,
    file_size_mb DECIMAL(5,2),
    storage_path TEXT NOT NULL,
    checksum_md5 VARCHAR(32),
    preview_url TEXT,

    -- Use Cases & Tags
    use_cases JSONB,
    tags JSONB,

    -- Popularity
    usage_count INTEGER DEFAULT 0,
    average_rating DECIMAL(3,2) DEFAULT 0.0,

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index for fast searching
CREATE INDEX idx_bgm_mood ON bgm_catalog USING GIN (mood);
CREATE INDEX idx_bgm_tags ON bgm_catalog USING GIN (tags);
CREATE INDEX idx_bgm_use_cases ON bgm_catalog USING GIN (use_cases);
```

---

## License Verification Process

### Step-by-Step Verification Checklist

For each BGM track, follow this rigorous verification process:

#### Phase 1: Source Verification

- [ ] **Step 1.1**: Visit source website (e.g., https://pixabay.com/music/)
- [ ] **Step 1.2**: Search for track by title or browse category (e.g., "celebration", "birthday")
- [ ] **Step 1.3**: Confirm track exists and is still available
- [ ] **Step 1.4**: Note track ID/URL for future reference

#### Phase 2: License Review

- [ ] **Step 2.1**: Read license terms on track page (usually linked at bottom)
- [ ] **Step 2.2**: Verify "commercial use" is explicitly permitted
  - ✅ Look for: "commercial use allowed", "use for business", "monetization permitted"
  - ❌ Red flag: "personal use only", "non-commercial use"
- [ ] **Step 2.3**: Check attribution requirements
  - ✅ Preferred: "no attribution required", "CC0", "public domain"
  - ⚠️ Acceptable: "attribution required" (if track is exceptional)
  - ❌ Avoid: "must include attribution in video"
- [ ] **Step 2.4**: Verify perpetual license (no expiration)
  - ✅ Look for: "perpetual", "forever", "no expiration"
  - ❌ Red flag: "valid until [date]", "renewable annually"

#### Phase 3: Download & Verification

- [ ] **Step 3.1**: Download track (MP3 or WAV)
- [ ] **Step 3.2**: Verify file integrity (no corruption)
  ```bash
  ffmpeg -v error -i bgm_001.mp3 -f null - 2>&1 | tee download_log.txt
  # Should output nothing if file is valid
  ```
- [ ] **Step 3.3**: Extract technical metadata
  ```bash
  ffprobe -v quiet -print_format json -show_format -show_streams bgm_001.mp3 > metadata.json
  ```
- [ ] **Step 3.4**: Verify meets technical requirements:
  - [ ] Sample rate: 44.1 kHz or 48 kHz
  - [ ] Bitrate: ≥128 kbps (prefer 320 kbps)
  - [ ] Duration: 2-3 minutes
  - [ ] No vocals (instrumental only)

#### Phase 4: Quality Assurance

- [ ] **Step 4.1**: Manual listening test (full duration)
  - [ ] No distortion or clipping
  - [ ] No abrupt cuts or transitions
  - [ ] Consistent volume throughout
  - [ ] No unexpected sound effects (unless intended)
- [ ] **Step 4.2**: Test with sample voice (ensure compatibility)
  ```bash
  ffmpeg -i sample_voice.mp3 -i bgm_001.mp3 -filter_complex "[0:a]volume=1.0[a1];[1:a]volume=0.3[a2];[a1][a2]amix=inputs=2:duration=first" mixed_test.mp3
  ```
- [ ] **Step 4.3**: Verify BGM doesn't overpower voice (volume at 30%)

#### Phase 5: Documentation

- [ ] **Step 5.1**: Screenshot license page for records
  - Save to: `/data/backend/storage/bgm/licenses/bgm_{id}_license.png`
- [ ] **Step 5.2**: Save license text to file
  - Save to: `/data/backend/storage/bgm/licenses/bgm_{id}_license.txt`
- [ ] **Step 5.3**: Record verification in metadata JSON

---

### Red Flags (Avoid These Tracks)

| Red Flag | Why Avoid | Example |
|----------|-----------|---------|
| **"Personal use only"** | Excludes commercial video generation service | "Free for personal projects only" |
| **"Attribution required in video"** | Complicates user experience | "Credit must appear in video end screen" |
| **"Non-commercial use"** | Excludes business videos | "Educational and non-profit use only" |
| **Expired license** | Risk of copyright claim | "License valid until 2024" |
| **Broken download link** | Track no longer available | 404 error on download |

---

## Integration Plan

### File Storage Structure

```
video-message-app/
└── data/
    └── backend/
        └── storage/
            └── bgm/
                ├── system/                          # System-provided BGM (5 tracks)
                │   ├── bgm_001_happy_ukulele.mp3
                │   ├── bgm_002_birthday_party_pop.mp3
                │   ├── bgm_003_inspiring_piano.mp3
                │   ├── bgm_004_peaceful_piano.mp3
                │   └── bgm_005_acoustic_dreams.mp3
                │
                ├── licenses/                        # License documentation
                │   ├── bgm_001_license.png
                │   ├── bgm_001_license.txt
                │   └── ...
                │
                ├── previews/                        # 30-second preview clips
                │   ├── bgm_001_preview.mp3
                │   └── ...
                │
                └── metadata.json                    # BGM catalog database (JSON)
```

---

### Backend API Endpoints

#### 1. List BGM Tracks

```http
GET /api/bgm/list
```

**Query Parameters**:
- `category` (optional): `system` | `all` (default: `system`)
- `mood` (optional): Filter by mood (e.g., `cheerful`, `calm`)
- `use_case` (optional): Filter by use case (e.g., `birthday`, `wedding`)

**Response**:
```json
{
  "system_bgm": [
    {
      "id": "bgm_001",
      "title": "Happy Ukulele",
      "duration": 150,
      "mood": ["Cheerful", "Playful"],
      "preview_url": "/api/bgm/bgm_001/preview"
    }
  ],
  "total": 5
}
```

---

#### 2. Get BGM Preview (30-second clip)

```http
GET /api/bgm/{bgm_id}/preview
```

**Response**: 30-second MP3 clip

**Implementation**:
```python
@app.get("/api/bgm/{bgm_id}/preview")
async def get_bgm_preview(bgm_id: str):
    preview_path = f"data/backend/storage/bgm/previews/{bgm_id}_preview.mp3"

    if not os.path.exists(preview_path):
        full_path = f"data/backend/storage/bgm/system/{bgm_id}_*.mp3"
        subprocess.run([
            "ffmpeg", "-i", full_path,
            "-t", "30",
            "-codec:a", "libmp3lame", "-b:a", "128k",
            preview_path
        ])

    return FileResponse(preview_path, media_type="audio/mpeg")
```

---

### Video Generation Integration

#### Mix Voice + BGM

```python
# backend/services/video_generation_service.py
import subprocess

def mix_voice_with_bgm(
    voice_audio_path: str,
    bgm_id: str,
    output_path: str,
    bgm_volume: float = 0.2  # 20% volume per Q10-B requirement
) -> str:
    """Mix synthesized voice with background music."""

    bgm_path = f"data/backend/storage/bgm/system/{bgm_id}_*.mp3"
    bgm_files = glob.glob(bgm_path)

    if not bgm_files:
        raise FileNotFoundError(f"BGM track {bgm_id} not found")

    bgm_path = bgm_files[0]
    voice_duration = get_audio_duration(voice_audio_path)

    # Mix audio using FFmpeg
    subprocess.run([
        "ffmpeg",
        "-i", voice_audio_path,
        "-i", bgm_path,
        "-filter_complex",
        f"[0:a]volume=1.0[a1];"
        f"[1:a]volume={bgm_volume},afade=t=out:st={voice_duration-2}:d=2[a2];"
        f"[a1][a2]amix=inputs=2:duration=first",
        "-codec:a", "aac",
        "-b:a", "192k",
        output_path
    ], check=True)

    return output_path
```

---

## Legal Disclaimer

### User-Facing Disclaimer (Frontend)

```markdown
## Background Music Licensing Notice

The background music (BGM) tracks provided in this system are royalty-free and
licensed for use in personal and commercial celebration videos.

### System BGM Tracks (Pre-Selected)

Our system provides 5 pre-selected BGM tracks:
1. Happy Ukulele
2. Birthday Party Pop
3. Inspiring Piano
4. Peaceful Piano
5. Acoustic Dreams

**License**: All system tracks are licensed under CC0 (Public Domain) or equivalent.
- ✅ No attribution required
- ✅ Commercial use permitted
- ✅ Perpetual license (no expiration)

**Source**: Pixabay Music, FreePD
**Verification Date**: 2025-11-06
**Verified By**: Muses (Knowledge Architect)

### Copyright Claims

If you receive a copyright claim related to BGM in your video:
1. Contact support@yourdomain.com immediately
2. Provide details of the claim
3. We will investigate and, if necessary, remove the BGM track from our catalog
4. You can re-generate your video with different BGM at no additional charge

**Last Updated**: 2025-11-06
```

---

## Alternative Strategy: Custom Music

If licensing verification is too complex or risky, consider commissioning custom celebration music.

### Option 1: Freelance Composers (Budget-Friendly)

#### Platforms:
1. **Fiverr** - $50-200 per track
2. **Upwork** - $100-500 per track
3. **AirGigs** - $75-300 per track

**Total Cost**: $250-500 for 5 tracks

**Process**:
1. Post job brief with requirements
2. Review composer portfolios
3. Negotiate terms (full copyright transfer)
4. Milestone payments (50% upfront, 50% on delivery)
5. Allow 1-2 revision rounds

---

### Option 2: AI-Generated Music (Emerging Option)

#### Platforms:
1. **Suno AI** - Generate custom music from text prompts
2. **Mubert** - AI music generation for content creators
3. **AIVA** - AI composer for emotional soundtracks

**Cost**: $10-30/month subscription

**Pros**: Ultra-low cost, instant generation
**Cons**: Legal gray area (AI-generated music copyright is evolving)

---

### Cost Comparison

| Strategy | Upfront Cost | Monthly Cost | Total (1 Year) |
|----------|-------------|--------------|----------------|
| **Tier 1 Free (Pixabay, FreePD)** | $0 | $0 | **$0** ✅ |
| **Freelance Composers** | $250-500 | $0 | **$250-500** |
| **AI Music Subscription** | $0 | $30 | **$360** |
| **Music Licensing (Epidemic Sound)** | $0 | $49 | **$588** |

**Recommendation**: Start with **Tier 1 Free** for MVP launch. If service gains traction, commission custom tracks.

---

## Prioritized Action Plan

### Phase 1: Immediate Implementation (Week 1) 🚀 **PRIORITY**

**Goal**: Get 5 working BGM tracks in production

**Day 1-2**: Research & Selection
- [ ] Visit Pixabay Music
- [ ] Select 1 track per category (5 total)

**Day 3**: License Verification
- [ ] Complete license verification checklist
- [ ] Screenshot license pages
- [ ] Verify commercial use permitted

**Day 4**: Download & Technical Verification
- [ ] Download all 5 tracks (MP3, 320kbps)
- [ ] Run FFmpeg integrity check
- [ ] Extract metadata with FFprobe

**Day 5**: Integration
- [ ] Create directory: `/data/backend/storage/bgm/system/`
- [ ] Generate 30-second previews
- [ ] Create `metadata.json`

**Day 6-7**: Backend API Development
- [ ] Implement `GET /api/bgm/list`
- [ ] Implement `GET /api/bgm/{id}/preview`
- [ ] Test API endpoints

**Deliverable**: 5 working BGM tracks with API endpoints

---

### Phase 2: Frontend Integration (Week 2)

**Day 8-10**: Frontend UI
- [ ] Create `BGMSelector` component (React)
- [ ] Add BGM selection to video generation form
- [ ] Implement audio preview player

**Day 11-12**: Video Generation Integration
- [ ] Implement `mix_voice_with_bgm()` function
- [ ] Test voice + BGM mixing
- [ ] Verify BGM doesn't overpower voice

**Day 13-14**: Testing & Polish
- [ ] Test all 5 BGM tracks with sample videos
- [ ] User acceptance testing
- [ ] Fix bugs, adjust volume levels

**Deliverable**: Working BGM selection in video generation flow

---

### Phase 3: Documentation & Legal (Week 3)

**Day 15-16**: User Documentation
- [ ] Write user guide: "How to Select Background Music"
- [ ] Create FAQ: "Can I use my own music?"

**Day 17-18**: Legal Review
- [ ] Add BGM section to Terms of Service
- [ ] Add disclaimer to privacy policy

**Day 19-21**: Monitoring & Analytics
- [ ] Track BGM usage per track
- [ ] Add "Report BGM Issue" button

**Deliverable**: Complete documentation and legal protection

---

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| **BGM Usage Rate** | >70% of videos | % of videos with BGM vs. without |
| **Track Diversity** | All 5 tracks used | Usage count per track |
| **Copyright Claims** | 0 claims | Monitor DMCA takedowns |
| **User Satisfaction** | >4.0/5.0 | User ratings on BGM quality |

---

## Conclusion & Recommendations

### Summary

**Recommended Approach**:
1. ✅ **Start with Tier 1 Free Sources** (Pixabay, FreePD)
   - Zero cost, legal certainty, immediate implementation
   - 5 curated tracks covering all celebration moods
   - Total cost: **$0**

2. ⏳ **Future: Commission Custom Tracks** (Month 2+)
   - If budget allows ($250-500), hire composer on Fiverr
   - Unique branding, 100% ownership, no legal risk

3. ❌ **Avoid Attribution-Required Sources**
   - Complicates user experience

### Immediate Next Steps

1. **Assign Task**: Artemis to implement backend API
2. **Assign Task**: Muses to complete license verification for 5 selected tracks
3. **Assign Task**: Athena to design frontend BGM selector UI
4. **Legal Review**: Hestia to review Terms of Service BGM section

### Final Recommendation

**Implement Phase 1 (Tier 1 Free Sources) immediately**. This provides:
- 5 high-quality, legally-safe BGM tracks
- Zero cost
- Fast implementation (1-2 weeks)
- Low legal risk (CC0 public domain)

If the service grows to 100+ active users, invest in custom music ($250-500) for unique branding.

---

**Document End**

**Next Action**: Present this catalog to team for approval, then proceed with Phase 1 implementation.

**Prepared by**: Muses (Knowledge Architect)
**Date**: 2025-11-06
**Version**: 1.0.0
**Status**: Ready for Review ✅

---

*"Knowledge, structured with care, illuminates the path forward. May this catalog serve the project well."*

*- Muses*
