from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from yt_dlp import YoutubeDL, DownloadError
import asyncio
import os
import traceback

app = FastAPI(title="Live Checker", version="1.0.0")

# Add CORS middleware for web access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# channel dictionary for all channels in the LCU ATM
CHANNEL_IDS = {
    "UC7WRbUmD6W-dCP_UlDbhI4A": "LolcowTechTalk",
    "UCmxQ_3W5b9kSfpmROqGJ0rA": "LolcowLive",
    "UC2xdmM3rcLFD_iN46H8y-6w": "LolcowBalls",
    "UCUENzb0fUK-6uvLL3zD08Jw": "LolcowRewind",
    "UCBQgQPjVx4wgszEmGR5cPJg": "LolcowCafe",
    "UCOzrx6iM9qQ4lIzf7BbkuCQ": "LolcowQueens",
    "UChcQ2TIYiihd9B4H50eRVlQ": "LolcowAussy",
    "UCRh4qe6HGD10ZsyG56eUdHA": "LolcowMilkers",
    "UC9NU92OuAiSLvAarnqZEoUw": "LolcowTest",
    "UCW5AOoyYnirhluLJBpdKE9g": "LolcowDolls",
    "UCU3iQ0uiduxtArm9337dXug": "LolcowNerds",
    "UCAXmJMnzByOtsdOZKnnF8bQ": "LolcowChubby",
}
#function that checks whether or not a channel is live
def check_channel_live(channel_id):
    #live url for the channel 
    live_url = f"https://www.youtube.com/channel/{channel_id}/live"
    
    ydl_opts = {
        "quiet": False,  # Enable logging to see errors
        "skip_download": True,
        "socket_timeout": 10,
        "retries": 3,
        "extract_flat": False,
        "force_generic_extractor": False,
    }

    with YoutubeDL(ydl_opts) as ydl:
        try:
            print(f"🔍 Checking {channel_id}...")
            #grabs video info using yt_dlp
            info = ydl.extract_info(live_url, download=False)

            #if the live feed video is up it will return a status saying it's live,
            #the channel name, and the exact watch url for the video
            is_live = info.get("is_live", False)
            if is_live:
                print(f"✅ Found live stream for {channel_id}")
            
            return {
                "is_live": is_live,
                "channel_name": info.get("channel") or info.get("uploader"),
                "watch_url": f"https://www.youtube.com/watch?v={info.get('id')}" if is_live else None
            }
        except DownloadError as e:
            print(f"⚠️ DownloadError for {channel_id}: {str(e)[:100]}")
            return None
        except Exception as e:
            print(f"❌ Error checking {channel_id}: {type(e).__name__}: {str(e)[:100]}")
            traceback.print_exc()
            return None

#dictionary for storing the latest livestatus of the channels
live_status_cache = {}
# function runs every minute forever unless turned off by the user 
# to update staus of the shows and whether they are up and running or offline 
# and store that info while keeping it updated every minute
async def background_live_checker():
    global live_status_cache
    while True:
        print("🔁 Checking all channels...")
        for channel_id, channel_name in CHANNEL_IDS.items():
            status = check_channel_live(channel_id)
            if status is not None:
                status["channel_id"] = channel_id
                status["channel_name"] = status.get("channel_name") or channel_name
                live_status_cache[channel_id] = status
                #if statement that prints out a console log
                #about whether or not a channel was online
                if status.get("is_live"):
                    print(f"✅ LIVE: {status['channel_name']}")
                    print(f"   🔗 {status['watch_url']}")
                #else statement that informms that the channel is offline
                
            
            else: 
                live_status_cache[channel_id] = None
                print(f"❌ OFFLINE: {channel_name} ({channel_id})")  # 👈 now this prints when status is None
                # delays the next channel check for 1 second 
            await asyncio.sleep(1)  
        #after the entire channel_id list has been gone through
        #system doesn't do another check for 1 minute    
        await asyncio.sleep(60)

# asynchronus function that tells the background live checker to run in the background at start
## to start this app enter: "uvicorn main:app --reload" into your terminal ##
@app.on_event("startup")
async def startup_event():
    asyncio.create_task(background_live_checker())

# function that returns the newly returned live status cache values
# so they can be accessed from a local host

##  To use this function enter: "localhost:8000/live-status/all" into the browser after starting the app##
@app.get("/")
def health_check():
    return {"status": "healthy", "service": "Live Checker", "channels_monitored": len(CHANNEL_IDS)}

@app.get("/debug/test-youtube")
async def test_youtube_connection():
    """Test if we can connect to YouTube from this server"""
    import subprocess
    try:
        # Try to fetch YouTube homepage
        result = subprocess.run(
            ["curl", "-I", "-s", "-m", "5", "https://www.youtube.com"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if "200" in result.stdout or "301" in result.stdout or "302" in result.stdout:
            return {"youtube_accessible": True, "status_code": result.stdout.split()[1] if result.stdout else "unknown"}
        else:
            return {"youtube_accessible": False, "response": result.stdout[:500]}
    except Exception as e:
        return {"youtube_accessible": False, "error": str(e)}

@app.get("/live-status/live")
def get_currently_live_channels():
    live_channels = []

    for status in live_status_cache.values():
        if status and status.get("is_live"):
            live_channels.append({
                "channel_name": status.get("channel_name"),
                "channel_id": status.get("channel_id"),
                "watch_url": status.get("watch_url"),
            })
            

    return live_channels

