#!/bin/bash

# This script takes as an argument a txt file containing a list of YouTube
# URLs to download (e.g. config/batch.txt or config/batch_hand.txt)
# example usage: ./yt-dl.sh config/batch_hand.txt
# outputs are saved to output/[filename]

BASE_DIR="$(pwd)"
BATCH_FILE="$1"
BATCH_NAME="$(basename ${BATCH_FILE} .txt)"
OUTPUT_DIR="${BASE_DIR}/output/${BATCH_NAME}"
ARCHIVE_FILE="${BASE_DIR}/config/archive.txt"
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
    --no-warnings \
    --all-subs \
    --sub-format "${SUB_FORMAT}" \
    --sleep-requests 1.25 \
    --min-sleep-interval 60 \
    --max-sleep-interval 90 \
    --compat-options abort-on-error