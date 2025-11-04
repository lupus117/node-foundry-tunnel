#!/bin/bash

umask 0000

helpFunction()
{
   echo ""
   echo "Usage: $0 -a session_name -b model_name -c compute_type -d device -e paralell -q"
   echo -e "\t-a session_name to be prefixed to seperate speakers"
   echo -e "\t-b model_name, tiny, small, medium, large or distil-large-v3"
   echo -e "\t-c compute_type, int8, float16 or float32"
   echo -e "\t-d Device, cuda or cpu"
   echo -e "\t-e cpu threading option, paralell or serial"   
   exit 1 # Exit script after printing help
}

while getopts "a:b:c:d:e:q" opt
do
   case "$opt" in
      a ) session_name="$OPTARG" ;;
      b ) model_name="$OPTARG" ;;
      c ) compute_type="$OPTARG" ;;
      d ) device="$OPTARG" ;;
      e ) paralell="$OPTARG" ;;
      q ) quiet=true;;
      ? ) helpFunction ;; # Print helpFunction in case parameter is non-existent
   esac
done

# Print helpFunction in case parameters are empty
if [ -z "$session_name" ] || [ -z "$model_name" ] || [ -z "$compute_type" ] || [ -z "$device" ] || [ -z "$paralell" ]
then
   echo "Some or all of the parameters are empty";
   helpFunction
fi

# Begin script in case all parameters are correct
echo "session name  : $session_name"
echo "model name    : $model_name"
echo "compute type  : $compute_type"
echo "device        : $device"
echo "paralell mode : $paralell"

echo "audio files:"
ls /data/audio

echo "existing transcription folders"
ls /data/transcripts

echo "installed models (new ones will be installed from huggingface hub)"
ls /root/.cache/huggingface/hub/

echo "nvidia-smi info"
nvidia-smi | grep NVIDIA

if ! command -v ffmpeg >/dev/null 2>&1
then
   echo "ffmpeg could not be found"
   echo "installing ffmpeg"
   echo "updating repositories"
   apt update > /dev/null 2>&1
   echo "installing ffmpeg"
   apt install -y ffmpeg > /dev/null 2>&1

fi


echo "Transcribing $session_name"
if [ "$quiet" = true ]; then
   python3 /data/scripts/transcript.py $session_name -m $model_name -c $compute_type -d $device -p $paralell -q
else
   python3 /data/scripts/transcript.py $session_name -m $model_name -c $compute_type -d $device -p $paralell

fi
python3 /data/scripts/merge.py $session_name
python3 /data/scripts/format.py $session_name

echo "Finished"
