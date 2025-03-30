# public-police-footage

This repository is for the paper Constructing Datasets From Public Police Body Camera Footage by Jamie Rosas-Smith, Martijn Bartelds, Ruizhe Huang, Leibny Paola García-Perera, Karen Livescu, Dan Jurafsky, and Anjalie Field. It includes code for downloading and processing public police body-worn camera footage from YouTube. The resulting data is ready for training and fine-tuning of off-the-shelf ASR models, and we provide code for fine-tuning Whisper using our dataset.

## Requirements and Installation
Create a conda environment and install the packages in config/requirements.txt:
```
conda create -n police python=3.9 -y
conda activate police
pip install -r ./config/requirements.txt
```


## Downloading videos - base dataset
1. First, download the videos. You will need to pass a cookie file to the download script (see below "How to pass YouTube cookies"). Then, use the script yt-dlp.sh with a file list from the config directory to download videos:
```
# Download the hand-cleaned videos
./yt-dlp.sh config/batch_hand.txt

# Download the automatically cleaned videos
./yt-dlp.sh config/batch.txt

```
Outputs can then be found in the `output` folder

2. Run OCR to extract captions. This can be done with the python script ocr.py. The script takes as arguments the top-level directory containing video files (`--video_dir`), the directory containing json annotation files (`--anno_dir`, default = `annotations`), a directory to store outputs (`--output_dir`), where the outputs will preserve the directory structure of the video files. The script also takes a flag (`--hand`), which indicates if you are processing hand-corrected files and should take frame_start and frame_end times.

```
# Extract captions from the hand-cleaned videos
python ocr.py --video_dir output/batch_hand --hand --anno_dir annotations --output_dir output/batch_hand

# Extract captions from the automatically cleaned videos
python ocr.py --video_dir output/batch --anno_dir annotations --output_dir output/batch
```

3. [Optional] extract segments from audio. In steps #1 and #2, you will have fully downloaded and constructed the data. The script `conversion.py` can be used to convert the original video files into audio segments. This will result in many small files. The script takes as arguments the directory containing the video files (`--base_dir`), the directory containing the json caption files (`--anno_dir`) and a directory to write outputs (`--output_dir`). The script assumes that `--base_dir` and `--anno_dir` contain the same directory structure, which will be replicated in `--output_dir`.
```
# Clip hand-cleaned videos into audio segments, one corresponding to each caption
python conversion.py --base_dir output/batch_hand --anno_dir output/batch_hand --output_dir segment_test
```

4. [Optional] The notebook test_data.ipynb offers some functions to aid in exploring and validating the dowloaded data

## Downloading videos - custom data
1. New videos can be downloaded using the same `yt-dlp.sh` script. Add URLs to videos or public playlists to a config file in the same format as `config/batch.txt` and pass the new file to `yt-dlp.sh`. For example:
```
./yt-dlp.sh config/new_batch.txt

```
2. Extract on-screen captions with OCR: TODO


<!-- ## Running OCR - custom data
### CPU
1. To speed up the OCR and only run the OCR on body-worn camera footage, you may include a JSON annotation file for each video. The name of the annotations file should match the name of the video file (e.g. `video123.mp4` should be named `video123.json`). Your annotation files must follow the same structure of the provided JSON files under `annotations-json`.
2. Run:
```python ocr.py --video_dir path_to_videos --anno_dir path_to_custom_annotations
```
3. Output can be found under `output/ocr-[date-time]`

### GPU
... -->


### How to pass YouTube cookies to yt-dlp:

1. Download the [Get cookies.txt Clean](https://chromewebstore.google.com/detail/get-cookiestxt-clean/ahmnmhfbokciafffnknlekllgcnafnie?pli=1) Chrome extension.
2. Log in to the YouTube account you want to use to download.
3. Navigate to any page on YouTube.
4. Click the **Get cookies.txt** extension icon in your toolbar and a dialog will appear showing the list of cookies for the current page.
5. Click "Export As".
6. Navigate to your `police-data/config` directory.
7. Save cookies as `cookies.txt`.
 
Additional resources for using cookies with yt-dlp:
- [How to manually pass cookies](https://github.com/yt-dlp/yt-dlp/wiki/FAQ#how-do-i-pass-cookies-to-yt-dlp)
- [Tips on effectively exporting YouTube cookies](https://github.com/yt-dlp/yt-dlp/wiki/Extractors#exporting-youtube-cookies)
