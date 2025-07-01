# Resume Maker from Video

This project extracts audio from a video, transcribes it, and creates a summary. It's a pipeline of Python scripts that work together to process a video file and generate a text summary.

## Directory Structure

- `input/`: Place your input video files in this directory.
- `audio-from-input/`: Stores the extracted audio files from the input videos.
- `chunks/`: Stores the audio chunks created from the extracted audio.
- `raw_text/`: Stores the raw text transcripts from the audio chunks.
- `summaries/`: Stores the final summaries of the transcripts.
- `not_realated/`: This directory seems unrelated to the main workflow.
- `venv/`: Python virtual environment.

## Workflow

The process is divided into several steps, each handled by a specific Python script. You need to run them in the following order:

### 1. Extract Audio from Video

This step extracts the audio from a video file.

**Script:** `extract_audio.py`
**Input:** A video file in the `input/` directory.
**Output:** An audio file in the `audio-from-input/` directory.

### 2. Split Audio into Chunks

This step splits the audio file into smaller chunks.

**Script:** `split_audio.py`
**Input:** An audio file from the `audio-from-input/` directory.
**Output:** Audio chunks in a subdirectory inside the `chunks/` directory.

### 3. Transcribe Audio Chunks

This step transcribes the audio chunks into text.

**Script:** `transcribe_chunks_new.py`
**Input:** Audio chunks from a subdirectory in the `chunks/` directory.
**Output:** Raw text files in a subdirectory inside the `raw_text/` directory.

### 4. Merge Transcripts

This step merges the individual transcripts into a single file.

**Script:** `merge_transcripts.py`
**Input:** Raw text files from a subdirectory in the `raw_text/` directory.
**Output:** A merged transcript file.

### 5. Create Summary

This step creates a summary from the merged transcript.

**Script:** `create_summary.py`
**Input:** A merged transcript file.
**Output:** A summary file in a subdirectory inside the `summaries/` directory.

## Dependencies

To run these scripts, you will need to install the required Python libraries. You can find the necessary libraries by looking at the `import` statements at the beginning of each Python script.

**Note:** This project seems to be designed to process one video at a time. The subdirectories created in `chunks/`, `raw_text/`, and `summaries/` are likely named after the input file to keep the data organized.
