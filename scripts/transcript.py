import os
import subprocess
from datetime import timedelta
from faster_whisper import WhisperModel
#, BatchedInferencePipeline
import argparse

# Initialize the argument parser
parser = argparse.ArgumentParser(prog="faster-whisper session transcription", description="Transcribe audio files and add a session title to the output file names.")
parser.add_argument('session_title', type=str, help="Title for the transcription session, which will be prefixed to the output file names.")
parser.add_argument('-m', '--model')
parser.add_argument('-d', '--device')
parser.add_argument('-c', '--compute_type')
args = parser.parse_args()

# Path to the directory containing the audio files
tmpfiles = "/tmpfiles"
audio_dir = "/data/audio"
output_dir = f"/data/transcripts/{args.session_title}"

# Ensure the output directory exists
os.makedirs(output_dir, exist_ok=True)
os.makedirs(tmpfiles, exist_ok=True)

# Initialize the Whisper model
model = WhisperModel(args.model, device=args.device, compute_type=args.compute_type)  # Adjust device/computation type as needed
#model = BatchedInferencePipeline(model=_model)
#model sizes: tiny; base; small; medium; large
#compute types: int8; float16; float32
#devices: cpu - cpu; cuda - nvidia gpu, only newer ones with tenser cores get any real benefit.

# Global variable for chunk length in seconds
CHUNK_LENGTH_SECONDS = 1800  # 30 minutes by default



# Helper function to format seconds to hh:mm:ss, rounded to the nearest second
def seconds_to_hms(seconds):
    # Round to the nearest second
    seconds = round(seconds)
    return str(timedelta(seconds=seconds))

# Function checks if audio file (using path) is complately silent. Significantly speeds up dnd audio transcription due to the large sections of silence
def is_completely_silent(file_path):
    print("checking if silent")
    command = [
        "ffmpeg", "-i", file_path, "-af", "silencedetect=n=-35dB:d=1", "-f", "null", "-"
    ]
    result = subprocess.run(command, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
    #print(result)
    search_string = f"silence_duration: {CHUNK_LENGTH_SECONDS}"

    if search_string in result.stderr:
        return True  # Entire file is silent
    return False  # Not completely silent

# Helper function to split the audio file into smaller chunks using streaming
def split_audio(input_file, base_name, chunk_length_seconds=1800):  # Default to 30 minutes (1800 seconds)
    print("Splitting audio into chunks...")

    # Run ffmpeg to get the total duration of the input file
    result = subprocess.run(['ffmpeg', '-i', input_file], stderr=subprocess.PIPE, text=True)

    # Extract the duration in seconds from ffmpeg's stderr output
    duration_line = [line for line in result.stderr.splitlines() if "Duration" in line]
    if not duration_line:
        print("Error: Unable to determine the duration of the file.")
        return []
    
    duration = duration_line[0].split()[1]
    
    # Clean up the duration string by removing commas and other non-numeric characters
    duration = duration.replace(",", "").strip()

    try:
        # Convert duration to hours, minutes, and seconds
        h, m, s = map(float, duration.split(":"))
        total_duration_seconds = int(h * 3600 + m * 60 + s)
    except ValueError as e:
        print(f"Error: Failed to parse duration '{duration}'. {e}")
        return []

    print(f"Total duration: {total_duration_seconds} seconds")

    # Generate the chunk filenames and use ffmpeg to extract each segment
    chunks = []
    for start_time in range(0, total_duration_seconds, chunk_length_seconds):
        chunk_file = os.path.join(tmpfiles, f"{base_name}_chunk_{start_time}.mp3")

        # Use ffmpeg to split the file: seek to start_time and extract chunk_length_seconds duration
        subprocess.run([ 
            'ffmpeg', '-ss', str(start_time), '-i', input_file,
            '-t', str(chunk_length_seconds), '-acodec', 'copy', '-y', chunk_file
        ])
        chunks.append(chunk_file)

    return chunks

# Process each .mp3 file in the directory and transcribe it
def folder_to_txt():
    for file_name in os.listdir(audio_dir):
        if file_name.endswith(".mp3"):
            file_path = os.path.join(audio_dir, file_name)
            print(f"Processing file: {file_path}")

            # Remove the .mp3 extension from the file name
            base_name = os.path.splitext(file_name)[0]

            # Split the audio file into chunks (5-minute segments by default)
            chunks = split_audio(file_path, base_name, CHUNK_LENGTH_SECONDS)
            print(f"Split the audio into {len(chunks)} chunks.")

            # Track the cumulative time for the entire file
            cumulative_time = 0

            # Prepare the output file for the entire audio file
            output_file = os.path.join(output_dir, f"{args.session_title}_{base_name}.txt")
            with open(output_file, "w", encoding="utf-8") as f:
                # Process each chunk individually
                for chunk_file in chunks:
                    print(f"Transcribing chunk: {chunk_file}")

                    # Transcribe the audio chunk
                    
                    # check if segment is complately silent

                    if is_completely_silent(chunk_file) == False:

                        segments, _ = model.transcribe(chunk_file, language="en",vad_filter=True)#,batch_size=16)

                        # Process each transcription segment
                        for segment in segments:
                            start = segment.start  # Start time of the segment
                            end = segment.end      # End time of the segment
                            text = segment.text    # Transcribed text

                            # Adjust start and end times based on cumulative time
                            adjusted_start_time = start + cumulative_time
                            adjusted_end_time = end + cumulative_time

                            # Format times in hh:mm:ss, rounded to seconds
                            start_time = seconds_to_hms(adjusted_start_time)
                            end_time = seconds_to_hms(adjusted_end_time)

                            # Write the transcribed text to the output file
                            line = f"[{start_time} - {end_time}] {base_name}: {text}\n"
                            f.write(line)

                            # Print each transcribed line to the console
                            print(f"[{start_time} - {end_time}] {base_name}: {text}")
                    else:
                        print("Segment is complately silent")
                    # Update the cumulative time after processing the chunk
                    cumulative_time += CHUNK_LENGTH_SECONDS

            print(f"Transcript saved to: {output_file}")

            # Clean up the temporary chunk files after processing the current file
            for chunk_file in chunks:
                os.remove(chunk_file)
                print(f"Deleted temporary chunk file: {chunk_file}")

    print("Batch transcription complete!")

folder_to_txt()
