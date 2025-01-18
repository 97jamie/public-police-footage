#!/bin/bash

eval "$(conda shell.bash hook)"

if ! command -v conda &> /dev/null; then
    echo "Download failed; please install conda first"
    exit 1
fi

ENV_NAME="police"

if ! conda info --envs | grep -q "$ENV_NAME"; then
    echo "Creating conda environment..."
    conda create -n "$ENV_NAME" python=3.9 -y
fi

source activate "$ENV_NAME" || { echo "activating conda environment failed"; exit 1; }

if [ -f "./config/requirements.txt" ]; then
    echo "Installing Python packages from requirements.txt..."
    pip install -r ./config/requirements.txt
else
    echo "requirements.txt not found in ./config."
    exit 1
fi

BASE_DIR="$(pwd)"
OUTPUT_DIR="${BASE_DIR}/output/youtube"
ARCHIVE_FILE="${BASE_DIR}/config/archive.txt"
BATCH_FILE="${BASE_DIR}/config/batch.txt"
COOKIES_FILE="${BASE_DIR}/config/cookies.txt"

VIDEO_FORMAT="bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"
SUB_FORMAT="srt"

yt-dlp \
    --cookies "${COOKIES_FILE}" \
    --format "${VIDEO_FORMAT}" \
    --output "${OUTPUT_DIR}/%(channel_id)s/%(id)s.%(ext)s" \
    --yes-playlist \
    --ignore-errors \
    --download-archive "${ARCHIVE_FILE}" \
    --batch-file "${BATCH_FILE}" \
    --continue \
    --write-description \
    --write-info-json \
    --write-annotations \
    --quiet \
    --no-warnings \
    --all-subs \
    --sub-format "${SUB_FORMAT}" \
    --sleep-requests 1.25 \
    --min-sleep-interval 60 \
    --max-sleep-interval 90 \
    --compat-options abort-on-error