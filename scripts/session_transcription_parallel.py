import os
import subprocess
from datetime import timedelta
from faster_whisper import WhisperModel
import argparse
from concurrent.futures import ThreadPoolExecutor

# Initialize the argument parser
parser = argparse.ArgumentParser(description="Transcribe audio files and add a session title to the output file names.")
parser.add_argument('session_title', type=str, help="Title for the transcription session, which will be prefixed to the output file names.")
args = parser.parse_args()

# Path to the directories
tmpfiles = "/tmpfiles"
audio_dir = "/audio"
output_dir = "/transcripts"

# Ensure the output directories exist
os.makedirs(output_dir, exist_ok=True)
os.makedirs(tmpfiles, exist_ok=True)

# Initialize the Whisper model
model = WhisperModel("large", device="cpu", compute_type="int8")

#model sizes: tiny; base; small; medium; large
#compute types: int8; float16; float32
#devices: cpu - cpu; cuda - nvidia gpu, only newer ones with tenser cores get any real benefit.


# Global variable for chunk length in seconds
CHUNK_LENGTH_SECONDS = 300  # 5 minutes by default

# Helper function to format seconds to hh:mm:ss
def seconds_to_hms(seconds):
    seconds = round(seconds)
    return str(timedelta(seconds=seconds))

# Check if audio file is completely silent
def is_completely_silent(file_path):
    command = [
        "ffmpeg", "-i", file_path, "-af", "silencedetect=n=-35dB:d=1", "-f", "null", "-"
    ]
    result = subprocess.run(command, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
    search_string = f"silence_duration: {CHUNK_LENGTH_SECONDS}"
    return search_string in result.stderr

# Split the audio file into smaller chunks
def split_audio(input_file, base_name, chunk_length_seconds=CHUNK_LENGTH_SECONDS):
    result = subprocess.run(['ffmpeg', '-i', input_file], stderr=subprocess.PIPE, text=True)
    duration_line = [line for line in result.stderr.splitlines() if "Duration" in line]
    if not duration_line:
        print("Error: Unable to determine the duration of the file.")
        return []

    duration = duration_line[0].split()[1].replace(",", "").strip()
    h, m, s = map(float, duration.split(":"))
    total_duration_seconds = int(h * 3600 + m * 60 + s)

    chunks = []
    for start_time in range(0, total_duration_seconds, chunk_length_seconds):
        chunk_file = os.path.join(tmpfiles, f"{base_name}_chunk_{start_time}.mp3")
        subprocess.run([
            'ffmpeg', '-ss', str(start_time), '-i', input_file,
            '-t', str(chunk_length_seconds), '-acodec', 'copy', '-y', chunk_file
        ])
        chunks.append(chunk_file)

    return chunks

# Function to transcribe a single chunk
def transcribe_chunk(chunk_file, base_name, cumulative_time, output_file):
    print(f"Checking if chunk {chunk_file} is silent")
    if is_completely_silent(chunk_file):
        print(f"Chunk {chunk_file} is completely silent.")
        return

    segments, _ = model.transcribe(chunk_file, language="en")
    with open(output_file, "a", encoding="utf-8") as f:
        for segment in segments:
            start = segment.start + cumulative_time
            end = segment.end + cumulative_time
            text = segment.text

            start_time = seconds_to_hms(start)
            end_time = seconds_to_hms(end)
            line = f"[{start_time} - {end_time}] {base_name}: {text}\n"
            f.write(line)
            print(f"[{start_time} - {end_time}] {base_name}: {text}")

# Process each .mp3 file and transcribe using multithreading
def folder_to_txt():
    for file_name in os.listdir(audio_dir):
        if file_name.endswith(".mp3"):
            file_path = os.path.join(audio_dir, file_name)
            base_name = os.path.splitext(file_name)[0]
            chunks = split_audio(file_path, base_name, CHUNK_LENGTH_SECONDS)

            output_file = os.path.join(output_dir, f"{args.session_title}_{base_name}.txt")
            cumulative_time = 0

            # Use ThreadPoolExecutor for multithreading
            with ThreadPoolExecutor() as executor:
                futures = []
                for chunk_file in chunks:
                    futures.append(executor.submit(transcribe_chunk, chunk_file, base_name, cumulative_time, output_file))
                    cumulative_time += CHUNK_LENGTH_SECONDS

                # Wait for all threads to complete
                for future in futures:
                    future.result()

            # Cleanup temporary chunk files
            for chunk_file in chunks:
                os.remove(chunk_file)

    print("Batch transcription complete!")

folder_to_txt()

