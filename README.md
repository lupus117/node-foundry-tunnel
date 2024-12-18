# node-foundry-tunnel
 Simple node FoundryVTT and Cloudflare docker-compose project for hosting. 
 Utilises duplicati for optional file backuping.

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

create two .env files:
- tunnel.env 
    - TUNNEL_TOKEN=CopiedToken
- duplicati.env
    - SETTINGS_ENCRYPTION_KEY=whateverseemsgood
    - DUPLICATI__WEBSERVICE_PASSWORD=Yourpassword

Keep in mind if you set up duplicati on second/new device your SETTINGS_ENCRYPTION_KEY needs to be the same as the previous device to access previously made backups


### Commands

In the root folder of this git directory run:
docker-compose up -d (runs the docker containers in the background)

if you need to shut down the containers use
docker-compose down
just remember you need to run the first command again to have it run on startup
