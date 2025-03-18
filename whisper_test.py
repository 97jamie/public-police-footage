import whisper
from jiwer import wer
import json
import os
from whisper.normalizers import EnglishTextNormalizer
import random
import tqdm

normalizer = EnglishTextNormalizer()
model = whisper.load_model("turbo")
# result = model.transcribe("segment_test/UCedDHcqSgiaOk4J0vkAC5LQ/q6jhyIcumG0_2.wav")
# print(result["text"])

def test_all(segment_dir, anno_dir):
    for root, _, files in os.walk(anno_dir):
        for file in files:
            # Find and load annotations files
            if file.endswith(".json") and not "info" in file:
                anno_path = os.path.join(root, file)
                # Find and transcribe segments
                channel_dir = os.path.basename(root)
                segment_channel_dir = os.path.join(segment_dir, channel_dir)
                try:
                    test_one(segment_channel_dir, anno_path)
                except Exception as e:
                    print(f"Error reading segments for {anno_path}: {str(e)}")

def test_one(segment_channel_dir, anno_path):
    gold = []
    transcribed = []

    video_id = os.path.splitext(os.path.basename(anno_path))[0]
    with open(anno_path, 'r') as json_file:
        annotations = json.load(json_file)

        print("Processing", anno_path)
        for i,anno in tqdm.tqdm(enumerate(annotations)):
            segment_file = os.path.join(segment_channel_dir,  video_id + "_" + str(i + 1) + ".wav")
            result = model.transcribe(segment_file)
            gold.append(normalizer(anno["text"]))
            transcribed.append(normalizer(result["text"]))
        curr_wer = wer(gold, transcribed)
        print(video_id, len(annotations), curr_wer)


def sample_one(segment_dir, anno_dir):
    channels = os.listdir(segment_dir)
    random_channel = random.sample(channels, 1)[0]
    segments = os.listdir(os.path.join(segment_dir, random_channel))
    random_segment = random.sample(segments, 1)[0]
    print(random_channel, random_segment)
    segment_path = os.path.join(segment_dir, os.path.join(random_channel, random_segment))
    splits = random_segment.split("_")
    
    video_id = "_".join(splits[:-1])
    segment_id = int(splits[-1].replace(".wav", ""))
    anno_path = os.path.join(anno_dir, os.path.join(random_channel, video_id + ".json"))
    with open(anno_path, 'r') as json_file:
        annotations = json.load(json_file)
    return (segment_path, annotations[segment_id - 1])


