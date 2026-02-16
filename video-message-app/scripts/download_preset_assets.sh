#!/bin/bash
#
# Download preset background images and BGM tracks.
# Run this on EC2 after deployment to populate the preset assets.
#
# Usage:
#   chmod +x scripts/download_preset_assets.sh
#   ./scripts/download_preset_assets.sh
#
# The script downloads assets to the Docker shared volume storage.
# After running, restart containers: docker-compose restart backend

set -euo pipefail

STORAGE_DIR="${STORAGE_DIR:-/home/ec2-user/video-message-app/video-message-app/data/backend/storage}"
BG_DIR="${STORAGE_DIR}/presets/backgrounds"
BG_THUMB_DIR="${BG_DIR}/thumbnails"
MUSIC_DIR="${STORAGE_DIR}/presets/music"
MUSIC_PREVIEW_DIR="${MUSIC_DIR}/previews"

echo "=== Preset Asset Downloader ==="
echo "Storage: ${STORAGE_DIR}"

mkdir -p "${BG_DIR}" "${BG_THUMB_DIR}" "${MUSIC_DIR}" "${MUSIC_PREVIEW_DIR}"

# -------------------------------------------------------------------
# Background Images
# Source: Unsplash / Pexels (free commercial use, no attribution required)
#
# To customize: replace URLs below with your preferred images.
# Recommended: 1920x1080 or higher, JPEG format.
# -------------------------------------------------------------------

echo ""
echo "--- Downloading background images ---"

download_bg() {
    local id="$1"
    local url="$2"
    local ext="${3:-.jpg}"
    local dest="${BG_DIR}/${id}${ext}"

    if [ -f "${dest}" ]; then
        echo "  [skip] ${id} already exists"
        return
    fi

    echo "  [download] ${id}..."
    if curl -sL -o "${dest}" "${url}"; then
        echo "  [ok] ${id} ($(du -h "${dest}" | cut -f1))"
    else
        echo "  [FAIL] ${id} - download failed"
        rm -f "${dest}"
    fi
}

# Unsplash images (append ?w=1920&q=80 for optimized size)
download_bg "bg-pastel-confetti"  "https://images.unsplash.com/photo-1530103862676-de8c9debad1d?w=1920&q=80"
download_bg "bg-pink-balloons"    "https://images.pexels.com/photos/1071879/pexels-photo-1071879.jpeg?auto=compress&w=1920"
download_bg "bg-gold-bokeh"       "https://images.unsplash.com/photo-1516450360452-9312f5e86fc7?w=1920&q=80"
download_bg "bg-birthday-cake"    "https://images.pexels.com/photos/1729797/pexels-photo-1729797.jpeg?auto=compress&w=1920"
download_bg "bg-paper-flowers"    "https://images.unsplash.com/photo-1490750967868-88aa4f44baee?w=1920&q=80"
download_bg "bg-party-streamers"  "https://images.pexels.com/photos/1543762/pexels-photo-1543762.jpeg?auto=compress&w=1920"
download_bg "bg-starry-purple"    "https://images.unsplash.com/photo-1534796636912-3b95b3ab5986?w=1920&q=80"
download_bg "bg-rose-petals"      "https://images.pexels.com/photos/931177/pexels-photo-931177.jpeg?auto=compress&w=1920"
download_bg "bg-warm-sunset"      "https://images.unsplash.com/photo-1507400492013-162706c8c05e?w=1920&q=80"
download_bg "bg-silver-sparkle"   "https://images.unsplash.com/photo-1481277542470-605612bd2d61?w=1920&q=80"

# Generate thumbnails (300px wide) if ImageMagick is available
if command -v convert &>/dev/null; then
    echo ""
    echo "--- Generating thumbnails ---"
    for img in "${BG_DIR}"/bg-*.jpg; do
        [ -f "${img}" ] || continue
        local_name=$(basename "${img}")
        thumb="${BG_THUMB_DIR}/${local_name}"
        if [ ! -f "${thumb}" ]; then
            convert "${img}" -resize 300x -quality 70 "${thumb}" 2>/dev/null && \
                echo "  [thumb] ${local_name}" || \
                echo "  [skip] ${local_name} - convert failed"
        fi
    done
else
    echo ""
    echo "[info] ImageMagick not found. Thumbnails will fall back to full images."
    echo "       Install with: sudo yum install -y ImageMagick"
fi

# -------------------------------------------------------------------
# BGM Tracks
# Sources: Bensound (CC-BY 3.0), Pixabay License, Kevin MacLeod (CC-BY 3.0)
#
# IMPORTANT: For CC-BY licensed tracks, attribution is required.
# Attribution info is stored in music_metadata.json.
#
# To customize: replace URLs below. Recommended: MP3, 128-192kbps.
# -------------------------------------------------------------------

echo ""
echo "--- Downloading BGM tracks ---"

download_bgm() {
    local id="$1"
    local url="$2"
    local ext="${3:-.mp3}"
    local dest="${MUSIC_DIR}/${id}${ext}"

    if [ -f "${dest}" ]; then
        echo "  [skip] ${id} already exists"
        return
    fi

    echo "  [download] ${id}..."
    if curl -sL -o "${dest}" "${url}"; then
        echo "  [ok] ${id} ($(du -h "${dest}" | cut -f1))"
    else
        echo "  [FAIL] ${id} - download failed"
        rm -f "${dest}"
    fi
}

# NOTE: These URLs may change over time. If a download fails, find
# alternative sources and update the URLs below.
#
# Bensound tracks: https://www.bensound.com/ (CC BY 3.0)
# Kevin MacLeod tracks: https://incompetech.com/ (CC BY 3.0)
# Pixabay tracks: https://pixabay.com/music/ (Pixabay License)

download_bgm "bgm-sunny"          "https://www.bensound.com/bensound-music/bensound-sunny.mp3"
download_bgm "bgm-jazz-piano"     "https://cdn.pixabay.com/audio/2022/02/22/audio_d1718ab41b.mp3"
download_bgm "bgm-happy-boy"      "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Happy%20Boy%20End%20Theme.mp3"
download_bgm "bgm-birthday-piano" "https://cdn.pixabay.com/audio/2024/11/04/audio_40bce5a4cd.mp3"
download_bgm "bgm-carefree"       "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Carefree.mp3"

# -------------------------------------------------------------------
# Summary
# -------------------------------------------------------------------

echo ""
echo "=== Download Summary ==="
echo "Backgrounds: $(ls -1 "${BG_DIR}"/bg-*.jpg 2>/dev/null | wc -l)/10"
echo "Thumbnails:  $(ls -1 "${BG_THUMB_DIR}"/bg-*.jpg 2>/dev/null | wc -l)/10"
echo "BGM tracks:  $(ls -1 "${MUSIC_DIR}"/bgm-*.mp3 2>/dev/null | wc -l)/5"
echo ""
echo "Storage usage:"
du -sh "${BG_DIR}" "${MUSIC_DIR}" 2>/dev/null || true
echo ""
echo "Done! Restart backend to serve assets: docker-compose restart backend"
