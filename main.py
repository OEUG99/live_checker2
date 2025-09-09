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
        # Try to bypass bot detection
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "referer": "https://www.youtube.com/",
        "extractor_args": {
            "youtube": {
                "player_client": ["android", "web"],
                "skip": ["hls", "dash", "translated_subs"],
            }
        },
        "http_headers": {
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        },
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
            error_msg = str(e)
            print(f"⚠️ DownloadError for {channel_id}: {error_msg[:200]}")
            
            # Check if it's a bot detection error
            if "Sign in to confirm" in error_msg or "bot" in error_msg.lower():
                print(f"🤖 Bot detection triggered for {channel_id} - YouTube is blocking Heroku IP")
                return {"error": "bot_detection", "channel_id": channel_id}
            
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
    bot_detection_count = 0
    
    while True:
        print("🔁 Checking all channels...")
        for channel_id, channel_name in CHANNEL_IDS.items():
            status = check_channel_live(channel_id)
            if status is not None:
                if status.get("error") == "bot_detection":
                    bot_detection_count += 1
                    print(f"🚫 Bot detection count: {bot_detection_count}")
                    live_status_cache[channel_id] = {"error": "bot_detection", "channel_name": channel_name}
                else:
                    status["channel_id"] = channel_id
                    status["channel_name"] = status.get("channel_name") or channel_name
                    live_status_cache[channel_id] = status
                    #if statement that prints out a console log
                    #about whether or not a channel was online
                    if status.get("is_live"):
                        print(f"✅ LIVE: {status['channel_name']}")
                        print(f"   🔗 {status['watch_url']}")
            else: 
                live_status_cache[channel_id] = None
                print(f"❌ OFFLINE: {channel_name} ({channel_id})")
                
            # delays the next channel check for 1 second 
            await asyncio.sleep(1)  
            
        # If too many bot detections, wait longer
        if bot_detection_count > 5:
            print(f"⏳ Too many bot detections ({bot_detection_count}), waiting 5 minutes...")
            await asyncio.sleep(300)  # Wait 5 minutes
            bot_detection_count = 0  # Reset counter
        else:
            await asyncio.sleep(60)  # Normal 1 minute wait

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
    bot_blocked = sum(1 for s in live_status_cache.values() if s and s.get("error") == "bot_detection")
    return {
        "status": "healthy" if bot_blocked < len(CHANNEL_IDS) else "degraded",
        "service": "Live Checker",
        "channels_monitored": len(CHANNEL_IDS),
        "bot_blocked_channels": bot_blocked,
        "message": "YouTube is blocking Heroku servers" if bot_blocked > 0 else "All systems operational"
    }

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
    bot_blocked_channels = []

    for status in live_status_cache.values():
        if status:
            if status.get("error") == "bot_detection":
                bot_blocked_channels.append(status.get("channel_name"))
            elif status.get("is_live"):
                live_channels.append({
                    "channel_name": status.get("channel_name"),
                    "channel_id": status.get("channel_id"),
                    "watch_url": status.get("watch_url"),
                })
    
    result = {"live_channels": live_channels}
    
    if bot_blocked_channels:
        result["warning"] = "YouTube is blocking requests from this server (bot detection)"
        result["blocked_channels"] = bot_blocked_channels
        
    return result

