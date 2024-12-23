import re
from collections import defaultdict

let transcripts = "/transcripts"
let output = "/transcripts/polished/merged.txt"
def remove_duplicate_messages(input_lines):
    """
    Remove duplicate messages for each speaker, even if other speakers' messages intervene.
    Consecutive duplicates are replaced with the format: "Message (xCount)".
    """
    # Extract all unique speakers
    speakers = set()
    speaker_lines = defaultdict(list)

    # Parse lines and group messages by speaker
    for line in input_lines:
        match = re.match(r"\[(.*?) - (.*?)\] (.*?): (.*)", line)
        if match:
            start, end, speaker, text = match.groups()
            speakers.add(speaker)
            speaker_lines[speaker].append((start, end, text))

    # Process each speaker's messages
    processed_lines = []
    for speaker in speakers:
        last_message = None
        repeat_count = 0

        for i, (start, end, text) in enumerate(speaker_lines[speaker]):
            if text == last_message:
                repeat_count += 1
            else:
                if repeat_count > 0:
                    # Append the previous repeated message with the count
                    processed_lines.append(f"[{speaker_lines[speaker][i - 1][0]} - {speaker_lines[speaker][i - 1][1]}] {speaker}: {last_message} (x{repeat_count + 1})")
                # Append the current message
                processed_lines.append(f"[{start} - {end}] {speaker}: {text}")
                last_message = text
                repeat_count = 0

        # Handle trailing repeated message
        if repeat_count > 0:
            processed_lines.append(f"[{speaker_lines[speaker][-1][0]} - {speaker_lines[speaker][-1][1]}] {speaker}: {last_message} (x{repeat_count + 1})")

    # Order the processed lines by timestamp
    return order_lines_by_timestamp(processed_lines)

def parse_timestamp_to_seconds(timestamp):
    """Convert a timestamp in HH:MM:SS format to total seconds."""
    try:
        h, m, s = map(int, timestamp.split(":"))
        return h * 3600 + m * 60 + s
    except ValueError:
        return float('inf')  # Place invalid timestamps at the end

def order_lines_by_timestamp(input_lines):
    """Order lines by their first timestamp."""
    def extract_start_time(line):
        match = re.match(r"\[(.*?) - .*?\]", line)
        return parse_timestamp_to_seconds(match.group(1)) if match else float('inf')

    return sorted(input_lines, key=extract_start_time)

def concatenate_transcripts(input_folder):
    """
    Concatenate all files in the /transcripts folder into a single merged file.
    """
    import os

    transcript_files = [
        os.path.join(input_folder, f)
        for f in os.listdir(input_folder)
        if os.path.isfile(os.path.join(input_folder, f))
    ]

    merged_lines = []
    for file_path in transcript_files:
        with open(file_path, "r", encoding="utf-8") as file:
            merged_lines.extend(file.readlines())

   # with open(output_file, "w", encoding="utf-8") as output:
    #    output.writelines(merged_lines)

    return merged_lines

# Example usage:
merged_lines = concatenate_transcripts(transcripts)
processed_lines = remove_duplicate_messages(merged_lines)
with open(output, "w", encoding="utf-8") as file:
    file.writelines("\n".join(processed_lines))
