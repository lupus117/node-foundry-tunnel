# node-foundry-tunnel
 Simple node FoundryVTT and Cloudflare docker-compose project for hosting. 
 Utilises duplicati for optional file backuping.
 Additional functionality for TTRPG session transcriptions using the faster-whisper service.

 Useful for people who cannot use port-forwarding for whatever reason and those who like to containerise for fun and safety.

 I've tried to make the setup process as simple as possible. 

 Prerequisites:
 - WSL 2 or another os capable of Linux containers.
 - Docker-compose installed on WSL 2 or the Linux OS

Foundry adresses: 
http://localhost:30000
https://subdomain.yourdomain

Duplicati adresses:
http://localhost:30001


## Instructions
Unpack official foundry.zip file and name "FoundryVTT"
create folder named data

### Cloudflare Tunnels

You need a domain on cloudflare.com
Under Zero Trust you need to create a new application with the desired subdomain name and desired access policies.
Under Networks - Tunnels, create a new tunnel. Use the subdomain name of the application earlier and the service as HTTP://foundry:30000

Under the different options for hosting choose docker. Copy the token section, only the token itself and not "--token TOKEN". Then paste it in the tunnel.env file as shown below.

Create tunnel.env file with the following line:
TUNNEL_TOKEN=CopiedToken

Create duplicati.env file with the following lines:
SETTINGS_ENCRYPTION_KEY=whateverseemsgood
DUPLICATI__WEBSERVICE_PASSWORD=Yourpassword

### Commands

In the root folder of this git directory run:
docker-compose up -d (runs the docker containers in the background)

If you need to shut down the containers use
docker-compose down

Just remember you need to run the first command again to have it run on startup


### duplicati (optional)
The first duplicati backup should be done after the initial configuration of foundry. Such that the foundry key is entered and admin user capable of creating worlds.
To save the configuration of the foundry key you need to shut down the docker container for foundry first.

docker-compose down

docker-compose up -d duplicati

you may then proceed to login by the password set by the DUPLICATI__WEBSERVICE_PASSWORD

Create a new backup, using your prefered method. I personally use Google drive to to the easy integration and having 60gb free. Run the backup and if there are no errors your configuration is successfully configured.

It is recommended to export the configuration file in the Duplicati web environment after backup setup. Encryption is recommended. Then storing that file on the cloud where you can ensure its longevity.

Keep in mind if you set up duplicati on new device your SETTINGS_ENCRYPTION_KEY needs to be the same as the previous device to access previously made backups, you can use the configuration file from earlier to make the process seemless since docker containers are standardised.

If you ever need to use the restore files function, make sure that the foundry container is down first.

After the initial setup, in my experience it should be no problem to run the subsequent backups while foundry is active. There will be a few warnings for files currently used by Foundry, however it seems those are files which you already have a backup of from the initial backup so its no issue. If you want to be 100% on a backup you can always take down the foundry container before backing up.



#### faster-whisper
In case I wish to convert audio recordings from dnd sessions on with the craig bot, I get an audio file per participant in the call. I can then convert those into text using faster-whisper. doing this is somewhat more complex but I'll try and make it simple.

the models, compute-types and session name are all defined in the docker-compose.yml
simply drag the mp3 files with the speaker names into the audio folder and set the variables. 
NB! if you do not have an nvidia gpu, select cpu as the device and comment out the lines regarding the gpu. Feel free to alter the reservations for the cores and memory in case of cpu transcription. 

Once the container has finished running you should have a file in ./transcripts/SESSION_NAME/polished with the session name.txt.
Be sure to remove any old .mp3 files whenever needed, to make sure not to accidentally have lingering copies. if you see you have in fact created trancriptions with copies. remove the speaker.txt files and run docker compose run faster-whisper python3 /data/scripts/merge.py SESSION_NAME && /data/scripts/format.py SESSION_NAME


##### Dev log
Getting faster whisper working was difficult because I had to figure out how to run it as well as parse large files. If I wanted to upload long files, like is usual for dnd, It proved problematic as the memory filled up so fast and it was killed by linux before anything could happen. 

I worked alongside my research partner (chatgpt) and used what I know of python, programming and docker to figure out a solution. What I arrived on is splitting the audio  file into smaller files. The first solution I came accross was using a python library to split it into several pieces. However that option did not work due to the large filesizes being loaded into memory. The goal is to have a lightwheight container after all that does not vaccuum all resources. 

After research, using a stream with the FFMPEG library and cut it into smaller sizes as you process without loading it all seemed to do the trick. 

The plan was to take all the mp3 files in a folder, one by one segment them, transcribe them, delete the segmented temp files and name them according to the desired session name + file name. The file name of the seperate .mp3 files will be the player name. 

When it goes through and gives all the seperate trancript files, its a relatively easy step to combine them into one and sort by time. Then its just last polishes of files.



