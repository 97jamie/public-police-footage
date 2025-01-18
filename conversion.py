import subprocess
import os
import argparse
import logging
import traceback
import tempfile
import re
import shutil
import json

def setup_logging():
    logging.basicConfig(
        level=logging.INFO, 
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler()
        ]
    )
    logger = logging.getLogger('Audio Splicing')
    return logger

logger = setup_logging()

def splice_audio(input_wav, output_dir, base_filename, segments):
    if not segments:
        logger.warning(f"No segments provided for splicing {input_wav}. Skipping.")
        return

    for i, (start, end) in enumerate(segments):
        output_file = os.path.join(output_dir, f"{base_filename}_{i + 1}.wav")
        command = [
            "ffmpeg",
            "-i", input_wav,
            "-ss", str(start),
            "-to", str(end),
            "-c", "copy",  # Avoid re-encoding
            "-y",  # Overwrite if exists
            output_file
        ]

        logger.debug(f"Running ffmpeg command: {' '.join(command)}")

        try:
            subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            logger.info(f"Generated segment: {output_file}")
        except subprocess.CalledProcessError as e:
            logger.error(f"Error generating segment for {input_wav}: {e.stderr.decode().strip()}")


def convert_video_to_wav(video_path, temp_dir):
    base_name = os.path.splitext(os.path.basename(video_path))[0]
    wav_path = os.path.join(temp_dir, f"{base_name}.wav")
    
    command = [
        "ffmpeg",
        "-i", video_path,
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", "44100",
        "-ac", "2",
        "-y",
        wav_path
    ]

    logger.debug(f"Running ffmpeg command: {' '.join(command)}")

    try:
        subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        logger.info(f"Successfully converted {video_path} to {wav_path}")
        return wav_path
    except subprocess.CalledProcessError as e:
        logger.error(f"ffmpeg error while converting {video_path} to WAV: {e.stderr.decode().strip()}")
        logger.debug(traceback.format_exc())
        return None
    

def time_str_to_seconds(time_str):
    parts = time_str.strip().split(':')
    parts = [float(part) for part in parts]
    if len(parts) == 2:
        minutes, seconds = parts
        return minutes * 60 + seconds
    elif len(parts) == 3:
        hours, minutes, seconds = parts
        return hours * 3600 + minutes * 60 + seconds
    else:
        logger.warning(f"Unrecognized time format: {time_str}")
        return 0.0


def process_annotation_file(anno_path):

    segments = []
    if os.path.exists(anno_path):
        try:
            with open(anno_path, 'r') as json_file:
                anno_data = json.load(json_file)  # Load JSON data
                for entry in anno_data:
                    if "start" in entry and "end" in entry:
                        segments.append((entry["start"], entry["end"]))
        except json.JSONDecodeError:
            logger.error(f"Failed to parse annotation file {anno_path}")
    else:
        logger.warning(f"Annotation file does not exist: {anno_path}")
    return segments


def main(base_dir, anno_dir, output_dir):
    temp_dir = tempfile.mkdtemp(prefix="video_to_wav_")
    logger.info(f"Created temporary directory for WAV conversions: {temp_dir}")

    try:
        for root, _, files in os.walk(base_dir):
            if root == base_dir:
                continue

            channel = os.path.basename(root)
            for file in files:
                if file.lower().endswith((".mp4", ".mov", ".avi", ".mkv")) and not file.endswith(".temp.mp4"):
                    video_path = os.path.join(root, file)
                    logger.info(f"Processing video file: {video_path}")

                    video_id = os.path.splitext(file)[0]
                    anno_filename = f"{video_id}.json"
                    anno_path = os.path.join(anno_dir, anno_filename)

                    if not os.path.exists(anno_path):
                        logger.warning(f"Skipping {video_path}: Annotation file {anno_path} does not exist")
                        continue

                    wav_path = convert_video_to_wav(video_path, temp_dir)
                    if not wav_path:
                        logger.error(f"Failed to convert {video_path} to WAV. Skipping.")
                        continue

                    segments = process_annotation_file(anno_path)
                    if not segments:
                        logger.warning(f"No valid segments found in {anno_path}. Skipping.")
                        continue

                    final_output_dir = os.path.join(output_dir, channel)
                    os.makedirs(final_output_dir, exist_ok=True)
                    logger.info(f"Output directory for segments: {final_output_dir}")

                    splice_audio(wav_path, final_output_dir, video_id, segments)

    finally:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        logger.info(f"Deleted temporary directory: {temp_dir}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Convert videos to WAV and splice based on timestamps')
    parser.add_argument('base_dir', type=str, help='Parent directory containing video files to process')
    parser.add_argument('anno_dir', type=str, help='Parent directory containing annotation files')
    parser.add_argument('output_dir', type=str, help='Directory to save spliced WAV files')

    args = parser.parse_args()

    main(args.base_dir, args.anno_dir, args.output_dir)