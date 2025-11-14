import os, shutil
import subprocess
from datetime import timedelta
from faster_whisper import WhisperModel
#, BatchedInferencePipeline
import argparse
import time
from concurrent.futures import ThreadPoolExecutor
import merge
import format
import re

def cleandir(folder: str):
    for filename in os.listdir(folder):
        file_path = os.path.join(folder, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print('Failed to delete %s. Reason: %s' % (file_path, e))

# Initialize the argument parser
parser = argparse.ArgumentParser(prog="faster-whisper session transcription", description="Transcribe audio files and add a session title to the output file names.")
#parser.add_argument('session_title', type=str, help="Title for the transcription session, which will be prefixed to the output file names.")
parser.add_argument('-m', '--model')
parser.add_argument('-d', '--device')
parser.add_argument('-c', '--compute_type')
parser.add_argument('-p', '--paralell_type', action="store_true", help="Enable quiet mode")
parser.add_argument('-q', '--quiet', action="store_true", help="Enable quiet mode")
parser.add_argument('-s', '--chunk_silence', action="store_false",help="Disables the checking if a chunk is silent.")
parser.add_argument('-l', '--chunk_length', type=int, default=1800, help="Set the chunk length in seconds")

args = parser.parse_args()

# Path to the directory containing the audio files
tmpfiles = "/tmpfiles"
audio_dir = "/data/audio"
output_dir = f"/data/transcripts/"
copy_dir = f"{output_dir}completed"
#polish_dir = f"{output_dir}/polished"

# Ensure the output directory exists
os.makedirs(output_dir, exist_ok=True)
os.makedirs(tmpfiles, exist_ok=True)
os.makedirs(copy_dir, exist_ok=True)

# Clean any possible remenants of an old run
cleandir(tmpfiles)
#cleandir(output_dir)
#cleandir(polish_dir)

# Initialize the Whisper model
model = WhisperModel(args.model, device=args.device, compute_type=args.compute_type)  # Adjust device/computation type as needed
#model sizes: tiny; base; small; medium; large
#compute types: int8; float16; float32
#devices: cpu - cpu; cuda - nvidia gpu, only newer ones with tenser cores get any real benefit.

# Global variable for chunk length in seconds
CHUNK_LENGTH_SECONDS = args.chunk_length  # 30 minutes by default

def qprint(input):
    if args.quiet == False:
        print(input)


# Helper function to format seconds to hh:mm:ss, rounded to the nearest second
def seconds_to_hms(seconds):
    # Round to the nearest second
    seconds = round(seconds)
    return str(timedelta(seconds=seconds))

# Function checks if audio file (using path) is complately silent. Significantly speeds up dnd audio transcription due to the large sections of silence
def is_completely_silent(file_path):
    qprint("checking if silent")
    command = [
        "ffmpeg", "-i", file_path, "-af", "silencedetect=n=-35dB:d=1", "-f", "null", "-"
    ]
    result = subprocess.run(command, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
    #qprint(result)
    search_string = f"silence_duration: {CHUNK_LENGTH_SECONDS}"

    if search_string in result.stderr:
        return True  # Entire file is silent
    return False  # Not completely silent

# Helper function to split the audio file into smaller chunks using streaming
def split_audio(input_file, base_name, chunk_length_seconds=1800):  # Default to 30 minutes (1800 seconds)
    qprint("Splitting audio into chunks...")

    # Run ffmpeg to get the total duration of the input file
    result = subprocess.run(['ffmpeg', '-i', input_file],stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    # Extract the duration in seconds from ffmpeg's stderr output
    duration_line = [line for line in result.stderr.splitlines() if "Duration" in line]
    if not duration_line:
        qprint("Error: Unable to determine the duration of the file.")
        raise ChildProcessError(f"Error: Unable to determine the duration of the file {input_file}.\n {str(result.stderr)}")
        return []
    
    #if len(result.stderr) > 3:
     #   raise ChildProcessError('Error in splitting files into chunks\n' + str(result.stderr))
         
    duration = duration_line[0].split()[1]
    
    # Clean up the duration string by removing commas and other non-numeric characters
    duration = duration.replace(",", "").strip()

    try:
        # Convert duration to hours, minutes, and seconds
        h, m, s = map(float, duration.split(":"))
        total_duration_seconds = int(h * 3600 + m * 60 + s)
    except ValueError as e:
        qprint(f"Error: Failed to parse duration '{duration}'. {e}")
        return []

    qprint(f"Total duration: {total_duration_seconds} seconds")


    # Generate the chunk filenames and use ffmpeg to extract each segment
    chunks = []
    for start_time in range(0, total_duration_seconds, chunk_length_seconds):
        chunk_file = os.path.join(tmpfiles, f"{base_name}_chunk_{start_time}.mp3")

        # Use ffmpeg to split the file: seek to start_time and extract chunk_length_seconds duration
        subprocess.run([ 
            'ffmpeg', '-ss', str(start_time), '-i', input_file,
            '-t', str(chunk_length_seconds), '-acodec', 'copy', '-y', chunk_file
        ],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        
        chunks.append(chunk_file)

    return chunks

def transcribe_chunk(chunk_file, base_name, cumulative_time, output_file):
    if args.chunk_silence:
        qprint(f"Checking if chunk {chunk_file} is silent")
        if is_completely_silent(chunk_file):
            qprint(f"Chunk {chunk_file} is completely silent.")
            return

    segments, _ = model.transcribe(chunk_file, language="en", vad_filter=True)
    with open(output_file, "a", encoding="utf-8") as f:
        for segment in segments:
            start = segment.start + cumulative_time
            end = segment.end + cumulative_time
            text = segment.text

            start_time = seconds_to_hms(start)
            end_time = seconds_to_hms(end)
            line = f"[{start_time} - {end_time}] {base_name}: {text}\n"
            f.write(line)
            if not args.quiet:
                qprint(f"[{start_time} - {end_time}] {base_name}: {text}")

# Process each .mp3 file in the directory and transcribe it
def folders_to_txt(dir_path :str):
    for fold_name in os.listdir(dir_path):
        if os.path.isdir(os.path.join(dir_path,fold_name)):
            stat = folder_to_txt(os.path.join(dir_path,fold_name),fold_name)
            print(f"Folder {fold_name} done with status {stat}")

def update_meta(folder_path: str, title, status,model,compute,device,audiofiles,start_time,error = ""):
    end_time = time.time()
    meta_path = os.path.join(folder_path,"metadata.txt")
    audio_count = len(audiofiles)
    if audio_count < 1:
        audio_count = 1
    meta = f"""Session title           = {title}
Status                  = {status}
faster-whisper model    = {model}
compute-type            = {compute}
device                  = {device}
audiofiles              = {[f"{a} " for a in audiofiles ]}
date and time of run    = {time.ctime(start_time)}
runtime                 = {seconds_to_hms(end_time - start_time)}
average runtime of file = {seconds_to_hms((end_time - start_time)/audio_count)}
completion at           = {time.ctime(end_time)}

{error}
        
"""
    with open(meta_path, "w",encoding="utf8") as f:
        f.writelines(meta)

def check_meta(fold_path: str, title, status,model,compute,device,audiofiles) -> bool:
    qprint("checking metadata")
    meta_path = os.path.join(fold_path,"metadata.txt")
    if os.path.exists(meta_path) is False:
        return False
    with open(meta_path,"r") as f:
        meta = (f.read()).split("\n")[:5]
    meta_cur = f"""Session title           = {title}
Status                  = {status}
faster-whisper model    = {model}
compute-type            = {compute}
device                  = {device}
audiofiles              = {[f"{a} " for a in audiofiles ]}
""".split("\n")[:5]
    #print("existing:\n",meta,"current:\n",meta_cur)
    if meta == meta_cur:
        return True
    else:
        return False


def folder_to_txt(folder_path: str, folder_name: str) -> str: 
    start_time = time.time()
    MODEL_NAME = args.model.replace("/","-")
    COMPUTE_TYPE = args.compute_type
    DEVICE = args.device
    AUDIOFILE_NAMES = []
    outfolder = os.path.join(output_dir,folder_name,MODEL_NAME)
    polish_dir = os.path.join(outfolder,"polished")
    os.makedirs(outfolder, exist_ok=True)
    os.makedirs(polish_dir, exist_ok=True) 
    def meta_update(status,error = "", files = AUDIOFILE_NAMES):
        update_meta(folder_path=polish_dir,title=folder_name,audiofiles=files,compute=COMPUTE_TYPE,device=DEVICE,start_time=start_time,error=error,status=status,model=MODEL_NAME)

    print("Transcribing: ",folder_path)
    _files = os.listdir(folder_path)
    files = []
    for file_name in _files:
        if file_name.endswith(".mp3"):
            files.append(file_name)
    transcription_needed = True
    if check_meta(polish_dir,folder_name,"Completed",MODEL_NAME,COMPUTE_TYPE,DEVICE,files) is True:
        print ("Folder ", folder_name,"Has already been transcribed with same paramaters")
        #print("metadata is equal")
        transcription_needed = False
    else:
        cleandir(outfolder)
    os.makedirs(outfolder, exist_ok=True)
    os.makedirs(polish_dir, exist_ok=True)

    meta_update("Started")
    if transcription_needed == True:
        for file_name in files:
            AUDIOFILE_NAMES.append(file_name)
            file_path = os.path.join(folder_path, file_name)
            qprint(f"Processing file: {file_path}")

            # Remove the .mp3 extension from the file name
            base_name = os.path.splitext(file_name)[0]
            meta_update("Transcribing "+ file_name)

            try:
                # Split the audio file into chunks (5-minute segments by default)
                chunks = split_audio(file_path, base_name, CHUNK_LENGTH_SECONDS)
                qprint(f"Split the audio into {len(chunks)} chunks.")

                # Track the cumulative time for the entire file
                cumulative_time = 0

                # Prepare the output file for the entire audio file
                output_file = os.path.join(outfolder, f"{base_name}.txt")

                if args.paralell_type == True:
                    qprint("printed lines will be out of order before formatting")
                    with ThreadPoolExecutor() as executor:
                        futures = []
                        for chunk_file in chunks:
                            futures.append(executor.submit(transcribe_chunk, chunk_file, base_name, cumulative_time, output_file))
                            cumulative_time += CHUNK_LENGTH_SECONDS

                        # Wait for all threads to complete
                        for future in futures:
                            future.result()
                else:
                # with open(output_file, "w", encoding="utf-8") as f:
                        # Process each chunk individually
                        for chunk_file in chunks:
                            qprint(f"Transcribing chunk: {chunk_file}")

                            # Transcribe the audio chunk
                            transcribe_chunk(chunk_file, base_name, cumulative_time, output_file)
                            cumulative_time += CHUNK_LENGTH_SECONDS

                qprint(f"Transcript saved to: {output_file}")

                # Clean up the temporary chunk files after processing the current file
                for chunk_file in chunks:
                    os.remove(chunk_file)
                    qprint(f"Deleted temporary chunk file: {chunk_file}")
            except Exception as e:
                print(f"Error in transcribing {file_name} in {folder_path}\n Error info in meta in {outfolder}/polished/metadata.txt")
                meta_update(f"Error in transcribing {file_name}",f"Error info: \n{str(e)}")
                return "Error"

    qprint("Batch transcription complete!")
    qprint("Merging and Fromatting transcripts")
    mergedfile = os.path.join(polish_dir,f"merged.txt")
    completed_file = os.path.join(polish_dir,f"{folder_name}.txt")
    completed_copy_dir = os.path.join(copy_dir,MODEL_NAME)
    os.makedirs(completed_copy_dir, exist_ok=True)
    completed_copy = os.path.join(completed_copy_dir,f"{folder_name}.md")
    headerfile = os.path.join(folder_path,"header.txt")
    header = ""
    if os.path.isfile(headerfile):
        with open(headerfile, "r") as f:
            header = f.read()
    try:
        merge.merge_folder(output_file=mergedfile,transcripts_folder=outfolder)
        format.format_with_header(merged_file=mergedfile,output_file=completed_file,header=header)
        format.format_with_header(merged_file=mergedfile,output_file=completed_copy,header=header,format="md")
    except Exception as e:
        print(f"Error in merging and formatting {outfolder} Error info in meta in {outfolder}/polished/metadata.txt")
        meta_update("Completed",str(e),files=files)
        return "Error"
    meta_update("Completed",files=files)
    with open(os.path.join(polish_dir,"metadata.txt"),"r", encoding="utf-8") as f:
        print(f.read())
    return "Completed"

folders_to_txt(audio_dir)
