# GPT Voice Website
Talk to GPT over Browser  

# Note:  
    While I made the server.py the /js/script.js file is entirely the creation of Pomme  
    https://github.com/Pxmme  
    https://twitter.com/pxmme1337  

# Install Notes (ubuntu 22.04/debian): 
    pip install -r requirements.txt    
    python3 server.py
  Define variables in server.py, add right url to script.js and index.html  
  Add index.html, /images/, recordings/, and /js/script.js to your webserver  
  Might be good to add the following cron:
    0 * * * * cd /path/to/your/recordings/ && find . -name "*.ogg" -type f -delete
    0 * * * * cd /path/to/your/recordings/ && find . -name "reply_*.mp3" -type f -delete
    @reboot nohup python3 /path/to/your/dir/server.py \&


# Demo: 
[![GPT Voice Website](https://img.youtube.com/vi/mGhKgAiBPrY/0.jpg)](https://youtu.be/mGhKgAiBPrY)  
donate for automation/scripting updates! https://www.patreon.com/Wintermute310  
 
