import re

merged_transcripts = "/transcripts/polished/merged.txt"
polished_transcripts ="/transcripts/polished/polished.txt"


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

def merge_speaker_lines(input_lines):
    # Process the lines as before, but after sorting them
    input_lines = order_lines_by_timestamp(input_lines)
    merged_lines = []
    current_speaker = None
    current_start = None
    current_end = None
    current_text = []
    indent_level = 15  # Set a fixed column for indentation

    last_line = ""
    line_repeat_count = 0

    for line in input_lines:
        # Match lines in the format: [start - end] Speaker: Text
        match = re.match(r"\[(.*?) - (.*?)\] (.*?): (.*)", line)
        if not match:
            continue

        start, end, speaker, text = match.groups()
        spkr = ""

        if speaker != current_speaker:
            # If speaker changes, finalize the current speaker's block
            if current_speaker and current_text:
                merged_lines.append(format_block(current_start, current_end, current_text, indent_level))
            # Reset for the new speaker
            current_speaker = speaker
            current_start = start
            current_text = []
            spkr = speaker
            line_repeat_count = 0
            current_text.append(f"{spkr}:")
        else:
            for i in range(len(speaker)): 
                spkr = ""# + spkr

        # Update the end time and add text
        current_end = end
        if last_line == text:
            line_repeat_count += 1
        else:
            if line_repeat_count > 0:
                current_text.append(f"{spkr}\t:")
                current_text.append(f"{last_line} (x{line_repeat_count})")
            current_text.append(f"{text}")
            line_repeat_count = 0
        last_line = text

    # Finalize the last block
    if current_speaker and current_text:
        merged_lines.append(format_block(current_start, current_end, current_text, indent_level))

    return merged_lines

def format_block(start, end, texts, indent_level):
    # Ensure that we don't try to format if the text is empty
    if not texts:
        return ""  # Prevent error if texts is empty
    # Create the formatted block with the start/end times and the first speaker line
    block = [f"[{start} - {end}] {texts[0]}"]
    # Add each subsequent line, ensuring proper indentation
    block.extend(f"{' ' * indent_level}{line}" for line in texts[1:] if line.strip())  # Skip empty lines
    return "\n".join(block)

def read_transcript_file(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            return file.readlines()
    except FileNotFoundError:
        print(f"Error: File '{file_path}' not found.")
        return []
    except Exception as e:
        print(f"Error reading file: {e}")
        return []

# Main testing function
def main():
    # Specify the test file
   # test_file = "cleaned_transcript.txt"  # Replace with your test file path
    print(f"Reading from file: {merged_transcripts}\n")
    input_lines = read_transcript_file(merged_transcripts)

    if not input_lines:
        print("No input lines found. Exiting.")
        return

    merged_output = merge_speaker_lines(input_lines)
    output_file = polished_transcripts

    # Save the merged output to a file
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("\n\n".join(merged_output))

    print(f"polished transcript saved to: {output_file}")
    print("\nPolished Output:\n")
    print("\n\n".join(merged_output))

if __name__ == "__main__":
    main()
