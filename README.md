# node-foundry-tunnel
 Simple node FoundryVTT and Cloudflare docker-compose project for hosting.

## Instructions
Unpack official foundry.zip file and name "FoundryVTT"
create folder named data

create two .env file:
- tunnel.env 
    - TUNNEL_TOKEN="secret"
- duplicati.env
    - SETTINGS_ENCRYPTION_KEY=whateverseemsgood
    - DUPLICATI__WEBSERVICE_PASSWORD=Yourpassword
