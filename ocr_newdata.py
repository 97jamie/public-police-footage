import cv2
import numpy as np
import easyocr
import os
import argparse
import re
from difflib import SequenceMatcher
from pprint import pprint
import traceback
from paddleocr import PaddleOCR
import logging

def convert_to_mm_ss(time_in_seconds):
    minutes, seconds = divmod(int(time_in_seconds), 60)
    return f"{minutes:02}:{seconds:02}"


def find_file(directory, path):
    base_filename = os.path.splitext(os.path.basename(path))[0] + ".txt"
    
    for root, dirs, files in os.walk(directory):
        if base_filename in files:
            return os.path.join(root, base_filename)
    return None


def process_footage_file(file_path):
    timestamps = []
    with open(file_path, 'r') as file:
        for line in file:
            start, end = (int(x) for x in line.split(','))
            timestamps.append((start, end))
    return timestamps


def has_overlap(timestamps, start_time, end_time):
    for start, end in timestamps:
        if (start < end_time and end > start_time):
            return True
    return False


def clean_text(text):
    clean = re.sub(r'[^a-zA-Z0-9\s]', '', text)  # remove special characters
    clean = clean.lower()  # convert to lower case
    clean = clean.rstrip(' ')
    clean = clean.lstrip(' ')
    return clean


def is_similar(s1, s2, threshold=0.6):
    s1_clean = clean_text(s1)
    s2_clean = clean_text(s2)
    result = SequenceMatcher(None,s1_clean,s2_clean).ratio()
    return result > threshold

def load_cmu_dict(file_path):
    cmu_dict = []

    with open(file_path, 'r', encoding='latin-1') as file:
        for line in file:
            # ignore lines that are comments
            if line.startswith('##'):
                continue

            # split the line into word and phones
            parts = line.strip().split('  ')
            if len(parts) == 2:
                word, _ = parts
                cleaned_word = word.lower().replace('"', '').replace('(', '').replace(')', '').replace('.', '').replace('-', '').replace("'", "")
                cmu_dict.append(cleaned_word)

    return cmu_dict

def is_unlikely_word(word):
    vowels = {'a', 'e', 'i', 'o', 'u'}
    sonorants = {'m', 'n', 'l', 'r', 'j', 'w'}
    vowels_and_sonorants = vowels.union(sonorants)

    if len(word) < 2:
        return True

    if not any(char in vowels_and_sonorants for char in word):
        return True

    unlikely_combinations = {'jh', 'td', 'cx', 'fx', 'tz', 'bf', 'fs', 'xp', 'ct', 'kv', 'cc', 'hg', 'hq', 'dg', 'zh', 'gd', 'tb', 'fj', 'df', 'gs', 'xc', 'js', 'bs', 'vb', 'ds', 'ss', 'kg', 'bc', 'bj', 'bg', 'fb', 'pv', 'qt', 'kc', 'xb', 'ts', 'dc', 'vf', 'cj', 'iu', 'kd', 'pc', 'hj', 'pt', 'dq', 'cv', 'hh', 'sd', 'tf', 'jc', 'bx', 'dp', 'bb', 'gf', 'sh', 'fh', 'hd', 'gk', 'cs', 'kk', 'tg', 'jv', 'hb', 'hv', 'pf', 'hf', 'tt', 'hx', 'jf', 'x', 'gg', 'dx', 'dz', 'dd', 'cf', 'ps', 'px', 'ks', 'sz', 'jd', 'vp', 'sq', 'cz', 'hp', 'kp', 'vt', 'fc', 'hs', 'tj', 'sf', 'cp', 'pk', 'xt', 'gv', 'ht', 'dt', 'bk', 'cq', 'gx', 'xf', 'kj', 'fg', 'xv', 'bt', 'kh', 'ff', 'fd', 'tk', 'qc', 'vv', 'fp', 'pq', 'gp', 'gc', 'dv', 'pj', 'dk', 'jb', 'jg', 'jt', 'pg', 'bv', 'dh', 'uu', 'ao', 'kb', 'kz', 'ck', 'sv', 'qb', 'qq', 'gz', 'ft', 'zz', 'pd', 'hc', 'kt', 'sg', 'tx', 'gj', 'hk', 'pp', 'sc', 'bp', 'vx', 'jp', 'tc', 'sj', 'xs', 'vs', 'ii', 'sb', 'kx', 'vc', 'hz', 'cg', 'bh', 'sk', 'st', 'sx', 'xx', 'pb', 'jj', 'tp', 'bd', 'qd'}

    if word in unlikely_combinations:
        return True

    return False

def contains_english(caption, cmu_dict):
    words = clean_text(caption).lower().split()
    for word in words:
        cleaned_word = word.replace('"', '').replace('(', '').replace(')', '').replace('.', '').replace('-', '').replace("'", "")
        if (cleaned_word in cmu_dict and not is_unlikely_word(cleaned_word)) or cleaned_word.isdigit():
            return True
    return False

def extract_text_paddle(frame, ocr_reader):
    upsample = cv2.resize(frame, (0, 0), fx=2, fy=2)
    hsv = cv2.cvtColor(upsample, cv2.COLOR_BGR2HSV)
    msk = cv2.inRange(hsv, np.array([0, 0, 123]), np.array([179, 255, 255]))
    result_all = ocr_reader.ocr(msk, cls=True)
    if result_all[0] != None:
        caption = []
        for i in range(len(result_all[0])):
            all_text = result_all[0][i][1][0]
            caption.append(all_text)
        joined = " ".join(caption)
        return joined
    else:
        return None


def ocr_captions(video_path, extraction_dir=None):
    extraction_path = find_file(extraction_dir, video_path) if extraction_dir else None
    cmu_dict = load_cmu_dict('/home/jrosass1/repos/police-scripts/cmudict-0.7b')

    try:
        video_capture = cv2.VideoCapture(video_path)
        fps = video_capture.get(cv2.CAP_PROP_FPS)
        logger = logging.getLogger('ppocr')
        logger.setLevel(logging.ERROR)
        reader = PaddleOCR()

        video_data = []

        current_entry = {}
        last_segment = None
        new_segment = False

        while True:
            ret, frame = video_capture.read()

            if not ret:
                break

            frame_count = int(video_capture.get(cv2.CAP_PROP_POS_FRAMES))

            start_time = frame_count / fps
            end_time = (frame_count + 1) / fps

            current_segment = None

            if extraction_path:
                processed_ext = process_footage_file(extraction_path)
                current_segment = has_overlap(processed_ext, start_time, end_time)

            if last_segment is None:
                last_segment = current_segment

            if not current_segment and extraction_path:
                continue

            if not new_segment:  # Handle segment transitions
                if last_segment != current_segment:
                    new_segment = True
                    last_segment = current_segment

            height, _, _ = frame.shape
            crop = int(2 * height / 3)
            cropped_frame = frame[crop:]

            caption = extract_text_paddle(cropped_frame, reader)

            if caption and contains_english(caption, cmu_dict):
                print(caption)
                if current_entry:
                    if is_similar(caption, current_entry["text"][-1][0], threshold=0.7) and not new_segment:
                        current_entry["end_time"] = end_time
                        current_entry["text"].append((caption, start_time, end_time))
                    else:
                        video_data.append(current_entry)
                        current_entry = {
                            "start_time": start_time,
                            "end_time": end_time,
                            "text": [(caption, start_time, end_time)]
                        }
                else:
                    current_entry = {
                        "start_time": start_time,
                        "end_time": end_time,
                        "text": [(caption, start_time, end_time)]
                    }

                new_segment = False

        if current_entry:
            video_data.append(current_entry)

        video_capture.release()
        video_data.sort(key=lambda x: x["start_time"])
        return video_data

    except Exception as e:
        print(f"Error processing file {video_path}: {str(e)}")
        traceback.print_exc()
        return []


def main(base_dir, footage_times, output_dir):
    output = []

    for root, dirs, files in os.walk(base_dir):

        if root == base_dir:
            continue

        for file in files:
            if file.endswith(".mp4") and not file.endswith(".temp.mp4"):
                file_path = os.path.join(root, file)
                print(f"Processing file: {file_path}")
                video_data = ocr_captions(file_path, extraction_dir)
                pprint(video_data)

                if len(video_data) > 0:
                    channel_dir = os.path.basename(os.path.dirname(root))
                    final_output_dir = os.path.join(output_dir, channel_dir)
                    print(f"Output directory: {final_output_dir}")
                    os.makedirs(final_output_dir, exist_ok=True)
                    output_file_path = os.path.join(final_output_dir, os.path.splitext(file)[0] + '.txt')

                    with open(output_file_path, 'w') as file:
                        for dictionary in video_data:
                            file.write(str(dictionary) + '\n')
                else:
                    print(f"Skipping file, no output: {file_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Extract OCR text from YouTube videos containing body camera footage')
    parser.add_argument('base_dir', type=str, help='Parent directory containing videos')
    parser.add_argument('output_dir', type=str, help='Directory to save the data')
    parser.add_argument('footage_times', type=str, help='Path to timestamps of body camera footage')

    args = parser.parse_args()

    main(args.base_dir, args.footage_times, args.output_dir)