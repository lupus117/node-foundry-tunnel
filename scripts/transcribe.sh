#!/bin/bash



helpFunction()
{
   echo ""
   echo "Usage: $0 -a session_name -b model_name -c compute_type -d device"
   echo -e "\t-a session_name to be prefixed to seperate speakers"
   echo -e "\t-b model_name, tiny, small, medium, large or distil-large-v3"
   echo -e "\t-c compute_type, int8, float16 or float32"
   echo -e "\t-d Device, cuda or cpu"
   exit 1 # Exit script after printing help
}

while getopts "a:b:c:d:" opt
do
   case "$opt" in
      a ) session_name="$OPTARG" ;;
      b ) model_name="$OPTARG" ;;
      c ) compute_type="$OPTARG" ;;
      d ) _device="$OPTARG" ;;
      ? ) helpFunction ;; # Print helpFunction in case parameter is non-existent
   esac
done

# Print helpFunction in case parameters are empty
if [ -z "$session_name" ] || [ -z "$model_name" ] || [ -z "$compute_type" ] || [ -z "$_device" ]
then
   echo "Some or all of the parameters are empty";
   helpFunction
fi

# Begin script in case all parameters are correct
echo "$session_name"
echo "$model_name"
echo "$compute_type"
echo "$_device"



nvidia-smi

apt update && apt install -y ffmpeg

echo "Transcribing $session_name"
python3 /data/scripts/transcript.py $session_name -m $model_name -c $compute_type -d $_device
python3 /data/scripts/merge.py $session_name
python3 /data/scripts/format.py $session_name

echo "Finished"