import cv2
import numpy as np
import os
import argparse
import json
from paddleocr import PaddleOCR
import logging
import traceback
import re

def auto_fix_caption(text):
    text = re.sub(r'\s+([,.!?])', r'\1', text)
    text = re.sub(r'\b(\w{2,})\s+s\b', r'\1s', text)
    text = re.sub(r"\b([a-zA-Z]+)\s+'\s+([a-zA-Z]+)\b", r"\1'\2", text)
    text = re.sub(
        r'^\s*(officer\s*\d*|officer|driver|community|subject|suspect|pa system|radio traffic|unknown)\s*[-:]?\s*',
        '', text, flags=re.I
    )

    if '"' in text:
        text = re.sub(r'^.*?"', '', text)
    
    return text

def convert_to_mm_ss(time_in_seconds):
    minutes, seconds = divmod(int(time_in_seconds), 60)
    return f"{minutes:02}:{seconds:02}"
    

def has_overlap(start_time, end_time, start_segment, end_segment):
    return (start_segment < end_time and end_segment > start_time)


def remove_before_colon(text):
    if ':' in text:
        return text.split(':', 1)[1].strip()
    return text

def remove_text_between_symbols(text):
    pattern = r'\(.*?\)|\[.*?\]|\*.*?\*'
    return re.sub(pattern, '', text).strip()

def replace_bleeped_curse_words(text):
    curse_word_replacements = {
        r'\bf[\*\-]*[u@]ck\b': 'fuck',
        r'\bf[\*\-]*[u@]cker\b': 'fucker',
        r'\bf[\*\-]*[u@]cking\b': 'fucking',
        r'\bs[\*\-]*h[i1]t\b': 'shit'
    }
    for pattern, replacement in curse_word_replacements.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return text

def normalize_chars(text):
    text = re.sub(r'[‐‑–—]', '-', text)  # normalize dashes
    text = re.sub(r'[•·◦●]', '', text)  # remove bullets
    text = re.sub(r'[^a-zA-Z0-9\s.,!?\'"-]', '', text)  # remove stray junk chars
    return text

def clean_caption_text(text, hand==False):
    text = remove_before_colon(text)
    text = remove_text_between_symbols(text)
    text = replace_bleeped_curse_words(text)
    text = normalize_chars(text)
    if not hand:
        text = auto_fix_caption(text)
    return text.strip()

def apply_replacements(entry, caption):
    to_replace = entry['to_replace']
    replace_with = entry['replace_with']
    if to_replace and replace_with:
        return caption.replace(to_replace, replace_with)
    return caption

def extract_text_paddle(frame, ocr_reader):
    upsample = cv2.resize(frame, (0, 0), fx=2, fy=2)
    hsv = cv2.cvtColor(upsample, cv2.COLOR_BGR2HSV)
    msk = cv2.inRange(hsv, np.array([0, 0, 123]), np.array([179, 255, 255]))
    result_all = ocr_reader.ocr(msk, cls=True)
    
    if result_all[0] is not None:
        caption = []
        for i in range(len(result_all[0])):
            all_text = result_all[0][i][1][0]
            caption.append(all_text)
        return " ".join(caption)
    return None


def ocr_captions(video_path, anno_data, reader, hand):
    if hand:
        start = "start_frame"
        end = "end_frame"
    else:
        start = "start"
        end = "end"
    try:
        logger = logging.getLogger('ppocr')
        logger.setLevel(logging.ERROR)

        video_capture = cv2.VideoCapture(video_path)
        if not video_capture.isOpened():
            print(f"Failed to open video file: {video_path}")
            return []
        
        fps = video_capture.get(cv2.CAP_PROP_FPS)
        if fps <= 0:
            print(f"Invalid FPS value for video file: {video_path}")
            video_capture.release()
            return []
        
        print(f"Processing video: {video_path} at {fps} FPS")

        video_data = []
        processed_entries = set()

        while True:
            ret, frame = video_capture.read()
            if not ret:
                break
            
            frame_count = int(video_capture.get(cv2.CAP_PROP_POS_FRAMES))
            start_time = frame_count / fps
            end_time = (frame_count + 1) / fps

            for i, entry in enumerate(anno_data):
                if i in processed_entries:
                    continue

                if start in entry and end in entry:
                    if has_overlap(start_time, end_time, entry[start], entry[end]):
                        height, _, _ = frame.shape
                        crop = int(2 * height / 3)
                        cropped_frame = frame[crop:]

                        caption = extract_text_paddle(cropped_frame, reader)
                        if caption:
                            entry_data = {
                                "start_time": entry["start"],
                                "end_time": entry["end"],
                                "text": apply_replacements(entry, caption) if 'to_replace' in entry else clean_caption_text(caption, hand),
                                "speaker": entry["speaker"] if 'speaker' in entry else ""
                           }
                            print(entry_data)
                            video_data.append(entry_data)
                            processed_entries.add(i)

        video_capture.release()
        video_data.sort(key=lambda x: x["start_time"])
        print(f"Finished processing video: {video_path}")
        return video_data

    except Exception as e:
        print(f"Error processing file {video_path}: {str(e)}")
        traceback.print_exc()
        return []



def main(base_dir, anno_dir, output_dir, hand):
    reader = PaddleOCR()

    print(f"Starting processing in base directory: {base_dir}")
    for root, _, files in os.walk(base_dir):
        for file in files:
            if file.endswith(".mp4") and not file.endswith(".temp.mp4"):
                file_path = os.path.join(root, file)
                print(f"Processing file: {file_path}")

                video_id = os.path.splitext(file)[0]
                anno_filename = f"{video_id}.json"
                anno_path = os.path.join(anno_dir, anno_filename)
                if os.path.exists(anno_path):
                    try:
                        with open(anno_path, 'r') as json_file:
                            anno_data = json.load(json_file)
                    except json.JSONDecodeError:
                        print(f"Failed to parse annotation file {anno_path}")
                        continue

                    video_data = ocr_captions(file_path, anno_data, reader, hand)
                else:
                    print(f"No annotation file found for {file_path}")
                    video_data = []

                if video_data:
                    channel_dir = os.path.basename(os.path.dirname(file_path))
                    final_output_dir = os.path.join(output_dir, channel_dir)
                    print(f"Output directory: {final_output_dir}")
                    os.makedirs(final_output_dir, exist_ok=True)
                    output_file_path = os.path.join(final_output_dir, os.path.splitext(file)[0] + '.json')

                    try:
                        with open(output_file_path, 'w') as outfile:
                            json.dump(video_data, outfile, indent=4)
                        print(f"Saved OCR captions to: {output_file_path}")
                    except Exception as e:
                        print(f"Failed to write output file {output_file_path}: {str(e)}")
                else:
                    print(f"Skipping file, no output generated: {file_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='OCR - caption extraction')
    parser.add_argument('--video_dir', type=str, help='Directory containing videos')
    parser.add_argument('--hand', action='store_true', help='Whether or not the annotations contain hand corrections')
    parser.add_argument('--anno_dir', type=str, default='annotations', help='Directory containing JSON annotations (default=annotations)')
    parser.add_argument('--output_dir', type=str, help='Directory to save the transcripts')

    args = parser.parse_args()
    main(args.video_dir, args.anno_dir, args.output_dir, args.hand)
