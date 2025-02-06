import subprocess
import sys
import os
import time
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import SessionNotCreatedException
from selenium.webdriver.chrome.options import Options
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import config_tv as config
import psutil
import requests
import enum
import unicodedata
import string
import random
from datetime import datetime, timedelta, timezone
import streamlink
from bs4 import BeautifulSoup
import re
from twitchAPI.twitch import Twitch
import asyncio
from google.auth.transport.requests import Request

t = time.localtime()
current_time = time.strftime("%H:%M:%S", t)
refresh = 15
token_url = f"https://id.twitch.tv/oauth2/token?client_id={config.client_id}&client_secret={config.client_secret}&grant_type=client_credentials"
APP_TOKEN_FILE = "client_secret.json"
GMAIL_TOKEN_FILE = "gmail_token.json"
USER_TOKEN_FILE = "user_token.json"
SCOPES_GMAIL = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/userinfo.profile',
  ]
SCOPES_BRAND = [
    'https://www.googleapis.com/auth/youtube.force-ssl',
    'https://www.googleapis.com/auth/userinfo.profile',
  ]
SCOPES = [
    'https://www.googleapis.com/auth/youtube.force-ssl',
    'https://www.googleapis.com/auth/userinfo.profile',
    'https://www.googleapis.com/auth/gmail.readonly',
  ]
home_dir = os.path.expanduser("~")
arguments = sys.argv
desired_url = "https://www.twitch.tv/" + config.username
bilibili_desired_url = "https://live.bilibili.com/" + config.username

async def offline_check(live_url, spare_link, important, titleforgmail):
    logging.info("Starting offline detection monitoring...")
    countdownhours = 0
    numberpart = 0
    fewtimes = 0
    gmailcount = 0
    countyt = 0
    
    while True:
        try:
            if countyt == 12:
                streams = streamlink.streams(f"https://www.youtube.com/watch?v={live_url}")
                if "best" in streams:
                    countyt = 0
                    pass
                else:
                    logging.info("The stream is dead or URL is not supported. Reloading stream...")
                    subprocess.run(["taskkill", "/f", "/im", config.apiexe])
                    titleforgmail = await checktitlelol(numberpart, important, "False", spare_link)
                    logging.info("finish reloading start spare stream")
                    logging.info("load spare stream")
                    if important == "schedule":
                        important = "schsheepedule"
                    elif important == "schsheepedule":
                        important = "schedule"
                    live_spare_url = await checktitlelol("0", important, "True", "Null")
                    subprocess.Popen(["start", config.apiexe], shell=True)
                    if config.unliststream == "True":
                        logging.info("public back the stream")
                        await public_stream(live_url)
                    logging.info("load offline_check again")
                    numberpart += 1
                    live_url = spare_link
                    spare_link = live_spare_url
                    logging.info(important)
                    countdownhours = 0
                    countyt = 0

            if config.Twitch == "True":
                # Initialize Twitch client
                twitch = await get_twitch_client()
                
                # Get streams
                streams = await get_twitch_streams(twitch, config.username)
                
                if not streams:
                    fewtimes += 1
                    if fewtimes == 6:
                        logging.info("Stream offline detected. Shutting down...")
                        if config.unliststream == "True":
                            logging.info("public back the stream")
                            await public_stream(live_url)
                        subprocess.run(["taskkill", "/f", "/im", config.apiexe])
                        subprocess.Popen(["start", "python", "check_tv.py", spare_link, important], shell=True)
                        exit()
            
            # Rest of your existing checks...
            if config.BiliBili == "True":
                try:
                    response = requests.get(f"https://live.bilibili.com/{config.username}")
                    soup = BeautifulSoup(response.text, 'html.parser')
                    ending_panel = soup.find("div", {"class": "web-player-ending-panel"})
                    
                    if ending_panel:  # Only increment fewtimes if ending panel is found
                        fewtimes += 1
                        if fewtimes == 6:
                            logging.info("Stream offline detected. Reloading program...")
                            if config.unliststream == "True":
                                logging.info("public back the stream")
                                await public_stream(live_url)
                            subprocess.run(["taskkill", "/f", "/im", config.apiexe])
                            subprocess.Popen(["start", "python", "check_tv.py", spare_link, important], shell=True)
                            exit()
                    else:  # Stream is still live
                        fewtimes = 0  # Reset counter if stream is live
                        
                except Exception as e:
                    logging.error(f"Error checking BiliBili stream: {e}")
                    pass

            # Update counters
            countdownhours += 1
            gmailcount += 1
            countyt += 1

            # Gmail check
            if gmailcount == 12:
                whatistheans = await find_gmail_title(titleforgmail)
                if whatistheans == "True":
                    logging.info("alert detect third party info restart stream to spare stream")
                    subprocess.run(["taskkill", "/f", "/im", config.apiexe])
                    titleforgmail = await checktitlelol(numberpart, important, "Null", spare_link)
                    logging.info("finish reloading start spare stream")
                    logging.info("load spare stream")
                    if important == "schedule":
                        important = "schsheepedule"
                    elif important == "schsheepedule":
                        important = "schedule"
                    live_spare_url = await checktitlelol("0", important, "True", "Null")
                    subprocess.Popen(["start", config.apiexe], shell=True)
                    if config.unliststream == "True":
                        logging.info("public back the stream")
                        await public_stream(live_url)
                    logging.info("load offline_check again")
                    numberpart += 1
                    live_url = spare_link
                    spare_link = live_spare_url
                    logging.info(important)
                    countdownhours = 0
                    gmailcount = 0
                else:
                    gmailcount = 0
            
            # Time limit check
            if countdownhours == 7871:
                logging.info("12 hour limit reached. Reloading stream...")
                subprocess.run(["taskkill", "/f", "/im", config.apiexe])
                titleforgmail = await checktitlelol(numberpart, important, "Null", spare_link)
                logging.info("finish reloading start spare stream")
                logging.info("load spare stream")
                if important == "schedule":
                    important = "schsheepedule"
                elif important == "schsheepedule":
                    important = "schedule"
                live_spare_url = await checktitlelol("0", important, "True", "Null")
                subprocess.Popen(["start", config.apiexe], shell=True)
                if config.unliststream == "True":
                    logging.info("public back the stream")
                    await public_stream(live_url)
                logging.info("load offline_check again")
                numberpart += 1
                live_url = spare_link
                spare_link = live_spare_url
                logging.info(important)
                countdownhours = 0

            await asyncio.sleep(5)  # Main loop delay
            
        except Exception as e:
            logging.error(f"Error in offline check: {str(e)}", exc_info=True)
            await asyncio.sleep(15)

async def get_twitch_client():
    twitch = Twitch(config.client_id, config.client_secret)
    await twitch.authenticate_app([])
    return twitch

async def get_twitch_streams(twitch, username):
    return [stream async for stream in twitch.get_streams(user_login=[username])]

async def get_twitch_stream_title():
    MAX_RETRIES = 3
    RETRY_DELAY = 5  # seconds
    
    for attempt in range(MAX_RETRIES):
        try:
            # Initialize Twitch client
            twitch = await get_twitch_client()
            
            # Get streams
            streams = await get_twitch_streams(twitch, config.username)
            
            if not streams:
                logging.info(f"No streams found (attempt {attempt + 1}/{MAX_RETRIES})")
                await asyncio.sleep(RETRY_DELAY)
                continue
                
            return streams[0].title
            
        except Exception as e:
            logging.error(f"Error getting Twitch stream info (attempt {attempt + 1}/{MAX_RETRIES}): {e}")
            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(RETRY_DELAY)
            else:
                logging.error("Max retries reached, returning fallback title")
                return f"Stream_{datetime.now().strftime('%Y-%m-%d')}"

async def load_check():
    logging.info("Waiting for stream to go live...")
    while True:
        try:
            if config.Twitch == "True":
                # Initialize Twitch client
                twitch = await get_twitch_client()
                
                # Get streams
                streams = await get_twitch_streams(twitch, config.username)
                
                if streams:
                    stream = streams[0]
                    logging.info(f"Stream is now live! Title: {stream.title}")
                    break
                else:
                    await asyncio.sleep(5)
            
            if config.BiliBili == "True":
                logging.info("Checking BiliBili stream status...")
                response = requests.get(f"https://live.bilibili.com/{config.username}")
                soup = BeautifulSoup(response.text, 'html.parser')
                ending_panel = soup.find("div", {"class": "web-player-ending-panel"})
                
                if not ending_panel:  # If ending panel is not found, stream is live
                    logging.info("Stream is now live!")
                    break
                time.sleep(5)

        except Exception as e:
            logging.error(f"Error checking stream status: {str(e)}")
            await asyncio.sleep(5)

async def selwebdriver_check(yt_link, infomation, driver):
    try:
        if driver == "Null":
            if yt_link == "Null":
                logging.info("Starting live API check to get initial stream URL")
                haha = "schsheepedule"
                live_url = await checktitlelol("0", haha, "True", "Null")
            else:
                live_url = yt_link
                haha = infomation

        if config.BiliBili == "True":
            try:
                response = requests.get(f"https://live.bilibili.com/{config.username}")
                soup = BeautifulSoup(response.text, 'html.parser')
                ending_panel = soup.find("div", {"class": "web-player-ending-panel"})
                
                if ending_panel:
                    logging.info("wait stream to start")
                    await load_check()
                    logging.info("load start")
                    await start_check(live_url, haha)
                else:
                    logging.info("load start immediately")
                    await start_check(live_url, haha)
                    
            except Exception as e:
                logging.error(f"Error checking BiliBili stream: {e}")
                pass
                
        if config.Twitch == "True":
            await load_check()
            logging.info("load start")
            await start_check(live_url, haha)
           
    except Exception as e:
        logging.error(f"Error: {e}")
        logging.info("the script failed shutting down")
        exit(1)  # Ensure the script exits with an error code

async def checkarg():
    try:
        arg1 = arguments[1]
        if arg1 == "KILL":
            logging.info("close all exe")
            subprocess.run(["taskkill", "/f", "/im", config.apiexe])
            subprocess.run(["taskkill", "/f", "/im", config.ffmpeg])
            subprocess.run(["taskkill", "/f", "/im", config.ffmpeg1])
            subprocess.run(["taskkill", "/f", "/im", "countdriver.exe"])
            exit()
        arg2 = arguments[2]
        logging.info("theres arg")
        try:
            await selwebdriver_check(arg1, arg2, "Null")
            exit()
        except Exception as e:
            logging.error(f"Script failed to execute: {e}")
            logging.info("failed script shutdown")
    except IndexError:  # Handle case where there are no arguments
        try:
            logging.info("theres no arg")
            await selwebdriver_check("Null", "Null", "Null")
        except Exception as e:
            logging.error(f"Failed to execute with null args: {e}")
            logging.info("failed script shutdown")
            exit()

async def start_check(live_url, haha):
    logging.info("Starting stream monitoring process...")
    logging.info("Launching streaming API process...")
    subprocess.Popen(["start", config.apiexe], shell=True)
    if haha == "schedule":
        logging.info("Starting scheduled stream relay...")
        subprocess.Popen(["start", "python", "relive_tv.py", "api_this"], shell=True)
        inport = "schsheepedule"
    if haha == "schsheepedule":
        logging.info("Starting alternate stream relay...")
        subprocess.Popen(["start", "python", "relive_tv.py", "this"], shell=True)
        inport = "schedule"
    logging.info(f"Stream URL configured: {live_url}")
    logging.info("Stream relay process started successfully")
    try:
        titleforgmail = await selwebdriver(live_url, haha)
    except UnboundLocalError:
        this_bug_is_unfixable = "sigh"
    logging.info("load spare stream")
    live_spare_url = await checktitlelol("0", inport, "True", "Null")
    logging.info("wait for offine now... and start countdown")
    await offline_check(live_url, live_spare_url, inport, titleforgmail)

class TwitchResponseStatus(enum.Enum):
    ONLINE = 0
    OFFLINE = 1
    NOT_FOUND = 2
    UNAUTHORIZED = 3
    ERROR = 4           

def check_process_running():
    process_name = "countdriver.exe"
    logging.info("Checking for existing browser automation processes...")
    for process in psutil.process_iter(['pid', 'name']):
        if process.info['name'] == process_name:
            logging.info("Browser automation process already running - waiting for completion...")
            time.sleep(15)
            check_process_running()
    logging.info("No conflicting processes found - proceeding...")
    return

def get_service():
    creds = None
    from google_auth_oauthlib.flow import InstalledAppFlow
    try:
        if os.path.exists(USER_TOKEN_FILE):
          # Load user credentials from a saved file
          if config.brandacc == "False":    
            creds = Credentials.from_authorized_user_file(USER_TOKEN_FILE, SCOPES)
          if config.brandacc == "True":
            creds = Credentials.from_authorized_user_file(USER_TOKEN_FILE, SCOPES_BRAND)
            
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
              if config.brandacc == "False":
                flow = InstalledAppFlow.from_client_secrets_file(APP_TOKEN_FILE, SCOPES, redirect_uri='urn:ietf:wg:oauth:2.0:oob')
                creds = flow.run_local_server(port=6971, brandacc="Nope")
              if config.brandacc == "True":
                flow = InstalledAppFlow.from_client_secrets_file(APP_TOKEN_FILE, SCOPES_BRAND, redirect_uri='urn:ietf:wg:oauth:2.0:oob')
                creds = flow.run_local_server(port=6971, brandacc="havebrand")
              with open(USER_TOKEN_FILE, 'w') as token:
                token.write(creds.to_json())
                
        return build('youtube', 'v3', credentials=creds)
        
    except Exception as e:
        logging.error(f"Error in get_service: {e}")
        exit(1)

def get_gmail_service():
    creds = None
    from google_auth_oauthlib.flow import InstalledAppFlow
    try:
        if config.brandacc == "True":
          if os.path.exists(GMAIL_TOKEN_FILE):
            creds = Credentials.from_authorized_user_file(GMAIL_TOKEN_FILE, SCOPES_GMAIL)
        if config.brandacc == "False":
          if os.path.exists(USER_TOKEN_FILE):
            creds = Credentials.from_authorized_user_file(USER_TOKEN_FILE, SCOPES)
            
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
              if config.brandacc == "True":
                logging.info("Gmail token not found. Starting authentication flow...")
                flow = InstalledAppFlow.from_client_secrets_file(APP_TOKEN_FILE, SCOPES_GMAIL, redirect_uri='urn:ietf:wg:oauth:2.0:oob')
                creds = flow.run_local_server(port=6971, brandacc="Nope")
                with open(GMAIL_TOKEN_FILE, 'w') as token:
                   token.write(creds.to_json())
              if config.brandacc == "False":
                logging.info("Gmail token not found. Starting authentication flow...")
                flow = InstalledAppFlow.from_client_secrets_file(APP_TOKEN_FILE, SCOPES, redirect_uri='urn:ietf:wg:oauth:2.0:oob')
                creds = flow.run_local_server(port=6971, brandacc="Nope")
                with open(USER_TOKEN_FILE, 'w') as token:
                   token.write(creds.to_json())
                
        return build('gmail', 'v1', credentials=creds)
        
    except Exception as e:
        logging.error(f"Error in get_gmail_service: {e}")
        exit(1)

def get_stream_linkandtitle():
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br'
        }
        
        response = requests.get(
            f"https://live.bilibili.com/{config.username}",
            headers=headers
        )
        response.encoding = 'utf-8'  # Ensure proper UTF-8 encoding
        soup = BeautifulSoup(response.text, 'html.parser')
        
        if soup.title:
            title = soup.title.string
            # Clean up the title by removing the suffix
            return re.sub(r' - .*', '', title)
        else:
            logging.warning("No title found on the page")
            return f"Stream_{datetime.now().strftime('%Y-%m-%d')}"

async def find_gmail_title(title):
    while True:
        try:
            service = get_gmail_service()
            # Get the current time and the time X minutes ago
            now = datetime.now()
            minutes_ago = now - timedelta(minutes=2)
            # Retrieve the latest 10 messages
            results = service.users().messages().list(userId='me', maxResults=2).execute()
            messages = results.get('messages', [])
            # Process the latest messages
            if messages:
                for message in messages:
                    msg = service.users().messages().get(userId='me', id=message['id']).execute()
                    # Convert the internalDate to a datetime object
                    received_time = datetime.fromtimestamp(int(msg['internalDate']) / 1000)
                    # Get the subject line of the message
                    subject = next((header['value'] for header in msg['payload']['headers'] if header['name'].lower() == 'subject'), '')
                    # Check if the message was received within the last X minutes and if the title is in the subject
                    if received_time >= minutes_ago and title in subject:
                        logging.info(f"Found message: {subject}")
                        return "True"
            return "False"
        except Exception as e:
            logging.error(f"Error in find_gmail_title: {e}")
            await asyncio.sleep(5)  # Use await here since it's an async function

def edit_live_stream(video_id, new_title, new_description):
  while True:
    try:
       service = get_service()
       category_id = '24'
       # Ensure new_title and new_description are strings, not coroutines
       if asyncio.iscoroutine(new_title):
           new_title = asyncio.run(new_title)
       if asyncio.iscoroutine(new_description):
           new_description = asyncio.run(new_description)
           
       request = service.videos().update(
             part="snippet",
             body={
                 "id": video_id,
                 "snippet": {
                     "title": str(new_title),  # Ensure string conversion
                     "description": str(new_description),  # Ensure string conversion
                     "categoryId": category_id
            }
        }
    )
       response = request.execute()
       return response['id']
       break
    except Exception as e:
      logging.info(f"Error: {e}")
      time.sleep(5)

def public_stream(live_id):
  while True:
    try:
       service = get_service()
       scheduled_start_time = datetime.now(timezone.utc).isoformat()
       request = service.videos().update(
           part='status',
           body={
               'id': live_id,
               'status': {
                   'privacyStatus': 'public'
               }
           }
       )
       response = request.execute()
       return response['id']
       break
    except Exception as e:
      logging.info(f"Error: {e}")
      time.sleep(5)

def create_live_stream(title, description, kmself):
    while True:
        try:
            service = get_service()
            scheduled_start_time = datetime.now(timezone.utc).isoformat()
                
            request = service.liveBroadcasts().insert(
                part="snippet,status,contentDetails",
                body={
                    "snippet": {
                        "title": title,
                        "description": description,
                        "scheduledStartTime": scheduled_start_time,
                    },
                    "status": {
                        "privacyStatus": kmself,
                        "selfDeclaredMadeForKids": False
                    },
                    "contentDetails": {
                        "enableAutoStart": True,
                        "enableAutoStop": True,
                        "latencyPrecision": "ultraLow"
                    }
                }
            )
            response = request.execute()
            return response['id']
        except Exception as e:
            logging.info(f"Error: {e}")
            time.sleep(5)

def api_load(url, brandacc):
      logging.basicConfig(filename="tv.log", level=logging.INFO, format='%(asctime)s %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
      logging.getLogger().addHandler(logging.StreamHandler())
      logging.info("create api keying ---edit_tv---")
      home_dir = os.path.expanduser("~")
      logging.info("run with countdriver.exe and check")
      check_process_running()
      subprocess.Popen(["start", "countdriver.exe"], shell=True)
      options = Options()
      chrome_user_data_dir = os.path.join(home_dir, "AppData", "Local", "Google", "Chrome", "User Data")
      options.add_argument(f"user-data-dir={chrome_user_data_dir}")
      options.add_argument(f"profile-directory={config.Chrome_Profile}")
      notafrickdriver = webdriver.Chrome(options=options)
      notafrickdriver.get(url)
      time.sleep(3)
      print(brandacc)
      if brandacc == "Nope":
          nameofaccount = f"//div[contains(text(),'{config.accountname}')]"
      if brandacc == "havebrand":
          nameofaccount = f"//div[contains(text(),'{config.brandaccname}')]"
      button_element = notafrickdriver.find_element("xpath", nameofaccount)
      button_element.click()
      time.sleep(3)
      element = notafrickdriver.find_element("xpath", "//div[@class='SxkrO']//button[@jsname='LgbsSe']")
      element.click()
      time.sleep(3)
      button_element = notafrickdriver.find_element("xpath", "(//button[@class='VfPpkd-LgbsSe VfPpkd-LgbsSe-OWXEXe-INsAgc VfPpkd-LgbsSe-OWXEXe-dgl2Hf Rj2Mlf OLiIxf PDpWxe P62QJc LQeN7 BqKGqe pIzcPc TrZEUc lw1w4b'])[2]")
      button_element.click()
      time.sleep(3)
      element = notafrickdriver.find_element("xpath", "//input[@class='VfPpkd-muHVFf-bMcfAe' and @type='checkbox']")
      element.click()
      time.sleep(1)
      button_element = notafrickdriver.find_element("xpath", "(//button[@class='VfPpkd-LgbsSe VfPpkd-LgbsSe-OWXEXe-INsAgc VfPpkd-LgbsSe-OWXEXe-dgl2Hf Rj2Mlf OLiIxf PDpWxe P62QJc LQeN7 BqKGqe pIzcPc TrZEUc lw1w4b'])[2]")
      button_element.click()
      subprocess.run(["taskkill", "/f", "/im", "countdriver.exe"])
      logging.info("finish idk ---edit_tv---")
      time.sleep(5)
      notafrickdriver.quit()

def confirm_logged_in(driver: webdriver) -> bool:
      """ Confirm that the user is logged in. The browser needs to be navigated to a YouTube page. """
      try:
            WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, "avatar-btn")))
            return True
      except Exception:
            logging.info("i domt know why it doesnot work lol")
            driver.quit()
            exit()

async def selwebdriver(live_url, timeisshit):
    if config.Twitch == "True":
        max_retries = 10
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                titletv = await get_twitch_stream_title()
                if not titletv:
                    status = TwitchResponseStatus.OFFLINE
                    logging.info("Stream appears to be offline, retrying...")
                else:
                    status = TwitchResponseStatus.ONLINE
                    break  # Success - exit the retry loop
            except Exception as e:
                retry_count += 1
                logging.error(f"Error getting Twitch stream title (attempt {retry_count}/{max_retries}): {e}")
                if retry_count >= max_retries:
                    status = TwitchResponseStatus.ERROR
                    logging.error("Max retries reached, using fallback title")
                    # Use a fallback title if all retries fail
                    titletv = "Stream[ERROR]"
                else:
                    await asyncio.sleep(2)  # Wait before retrying

    if config.BiliBili == "True":
        titletv = get_stream_linkandtitle()
    textnoemo = ''.join('' if unicodedata.category(c) == 'So' else c for c in titletv)
    if "<" in textnoemo or ">" in textnoemo:
        textnoemo = textnoemo.replace("<", "").replace(">", "")
    characters = string.ascii_letters + string.digits
    random_string = ''.join(random.choices(characters, k=7))
    filenametwitch = config.username + " | " + textnoemo + " | " + datetime.now().strftime("%Y-%m-%d")
    # Calculate max length for textnoemo to keep total under 100 chars
    if len(filenametwitch) > 100:
        max_textnoemo_length = 100 - len(config.username) - len(datetime.now().strftime("%Y-%m-%d")) - len(" | " * 2)
        textnoemo = textnoemo[:max_textnoemo_length-3] + "..."
        filenametwitch = config.username + " | " + textnoemo + " | " + datetime.now().strftime("%Y-%m-%d")
    if config.Twitch == "True":
        deik = f"this stream is from https://twitch.tv/{config.username} (Stream Name:{textnoemo})"
    if config.BiliBili == "True":
        deik = f"this stream is from https://live.bilibili.com/{config.username} (Stream Name:{textnoemo})"
    logging.info('process of edit name started')
    try:
        edit_live_stream(live_url, filenametwitch, deik)
        new_url = f"https://youtube.com/watch?v={live_url}"
        logging.info("wait to check live 40sec")
        await asyncio.sleep(40)
        if timeisshit == "schedule":
            check_is_live_api(new_url, config.ffmpeg1, "api_this")
        if timeisshit == "schsheepedule":
            check_is_live_api(new_url, config.ffmpeg, "this")
    finally:
        logging.info('edit finished continue the stream')
        return filenametwitch

def edit_rtmp_key(driver, what):
 countfuckingshit = 0
 while True:
  try:
    driver.find_element(By.XPATH, "//tp-yt-iron-icon[@icon='yt-icons:arrow-drop-down']").click()
    time.sleep(3)
    if what == "schedule":
        xpath = "//ytls-menu-service-item-renderer[.//tp-yt-paper-item[contains(@aria-label, '" + config.rtmpkeyname1 + " (')]]"
        element2 = driver.find_element(By.XPATH, xpath)
        element2.click()
        time.sleep(7)
    if what == "schsheepedule":
        xpath = "//ytls-menu-service-item-renderer[.//tp-yt-paper-item[contains(@aria-label, '" + config.rtmpkeyname + " (')]]"
        element3 = driver.find_element(By.XPATH, xpath)
        element3.click()
        time.sleep(7)
    if config.disablechat == "True":
        driver.find_element(By.XPATH, "//ytcp-button[@id='edit-button']").click()
        time.sleep(3)
        driver.find_element(By.XPATH, "//li[@id='customization']").click()
        time.sleep(2)
        driver.find_element(By.XPATH, "//*[@id='chat-enabled-checkbox']").click()
        time.sleep(1)
        driver.find_element(By.XPATH, "//ytcp-button[@id='save-button']").click()
    time.sleep(10)
    logging.info("finsih")
    driver.quit()
    subprocess.run(["taskkill", "/f", "/im", "countdriver.exe"])
    break
  except Exception as e:
        logging.info("error again")
        driver.refresh()
        time.sleep(15)
        countfuckingshit += 1
  if countfuckingshit == 3:
        logging.info("edit rtmp key fail shutdown script")
        subprocess.run(["taskkill", "/f", "/im", "countdriver.exe"])
        exit()

def check_is_live_api(url, ffmpeg, text):
      countshit = 0
      MAX_RETRIES = 3  # example upper bound
      while True:
            try:
                  print(url)
                  streams = streamlink.streams(url)
                  hls_stream = streams["best"]
                  logging.info('fucking live now')
                  break
            except KeyError as e:
                  logging.error(f'Stream not available: {str(e)}')
                  logging.info('The stream is messed up. Trying again...')
                  time.sleep(2)
                  subprocess.run(["taskkill", "/f", "/im", ffmpeg])
                  subprocess.Popen(["start", "python", "relive_tv.py", text], shell=True)
                  time.sleep(35)
                  countshit += 1
            if countshit >= MAX_RETRIES:
                  logging.info("Retry limit exceeded. Shutting down.")
                  subprocess.Popen(["start", "python", "check_tv.py", "KILL"], shell=True)
                  exit()

async def checktitlelol(arg1, arg2, reload, live_url):
    titletv = None  # Initialize titletv at the start
    
    if config.Twitch == "True" and reload == "False":
        max_retries = 10
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                titletv = await get_twitch_stream_title()
                if not titletv:
                    status = TwitchResponseStatus.OFFLINE
                    logging.info("Stream appears to be offline, retrying...")
                    retry_count += 1
                    await asyncio.sleep(5)
                    continue
                status = TwitchResponseStatus.ONLINE
                break  # Success - exit the retry loop
            except Exception as e:
                retry_count += 1
                logging.error(f"Error getting Twitch stream title (attempt {retry_count}/{max_retries}): {e}")
                if retry_count >= max_retries:
                    status = TwitchResponseStatus.ERROR
                    logging.error("Max retries reached, using fallback title")
                    titletv = "Stream[ERROR]"
                else:
                    await asyncio.sleep(5)  # Wait before retrying
            if not titletv:
                logging.error("Using fallback title")
                titletv = f"Stream_{datetime.now().strftime('%Y-%m-%d')}"

    if config.BiliBili == "True" and reload == "False":
        titletv = get_stream_linkandtitle()
        if not titletv:  # Fallback if neither Twitch nor BiliBili provided a title
          logging.error("Using fallback title")
          titletv = f"Stream_{datetime.now().strftime('%Y-%m-%d')}"
    if reload == "False":
        textnoemo = ''.join('' if unicodedata.category(c) == 'So' else c for c in titletv)
        if "<" in textnoemo or ">" in textnoemo:
            textnoemo = textnoemo.replace("<", "").replace(">", "")
        characters = string.ascii_letters + string.digits
        random_string = ''.join(random.choices(characters, k=7))
        calit = int(arg1) + 1
        filenametwitch = config.username + " | " + textnoemo + " | " + datetime.now().strftime("%Y-%m-%d") + " | " + "part " + str(calit)
        # Calculate max length for textnoemo to keep total under 100 chars
        if len(filenametwitch) > 100:
           max_textnoemo_length = 100 - len(config.username) - len(datetime.now().strftime("%Y-%m-%d")) - len(" | " * 3) - len("part " + str(calit))
           textnoemo = textnoemo[:max_textnoemo_length-3] + "..."
           filenametwitch = config.username + " | " + textnoemo + " | " + datetime.now().strftime("%Y-%m-%d") + " | " + "part " + str(calit)
        if len(filenametwitch) > 100:
           filenametwitch = config.username + " | " + datetime.now().strftime("%Y-%m-%d") + " | " + "part " + str(calit)
        if config.Twitch == "True":
           deik = f"this stream is from https://twitch.tv/{config.username} (Stream Name:{textnoemo})"
        if config.BiliBili == "True":
           deik = f"this stream is from https://live.bilibili.com/{config.username} (Stream Name:{textnoemo})"
    try:
        if reload == "True":
            filenametwitch = config.username + " (wait for stream title)"
            deik = "(wait for stream title)"
        if live_url == "Null":
            logging.info('sending to api')
            
            if config.unliststream == "True":
                live_url = create_live_stream(filenametwitch, deik, "unlisted")
            if config.unliststream == "False":
                live_url = create_live_stream(filenametwitch, deik, "public")
                
            logging.info('reading api json and check if driver loading')
            check_process_running()
            subprocess.Popen(["start", "countdriver.exe"], shell=True)
            options = Options()
            chrome_user_data_dir = os.path.join(home_dir, "AppData", "Local", "Google", "Chrome", "User Data")
            options.add_argument("user-data-dir=" + chrome_user_data_dir)
            options.add_argument("profile-directory=" + config.Chrome_Profile)
            while True:
                try:
                    driver = webdriver.Chrome(options=options)
                    break
                except SessionNotCreatedException:
                    abc = "abc"
            url_to_live = "https://studio.youtube.com/video/" + live_url + "/livestreaming"
            driver.get(url_to_live)
            time.sleep(5)
            driver.refresh()
            time.sleep(30)
            logging.info("edit the rtmp key and chat")
            if arg2 == "schedule":
                edit_rtmp_key(driver, "schedule")
            if arg2 == "schsheepedule":
                edit_rtmp_key(driver, "schsheepedule")
            driver.quit()
            subprocess.run(["taskkill", "/f", "/im", "countdriver.exe"])
        else:
            logging.info("edit the title of the url")
            edit_live_stream(live_url, filenametwitch, deik)
        if reload == "True":
            return live_url
        logging.info("start relive")
        if arg2 == "schedule":
            subprocess.Popen(["start", "python", "relive_tv.py", "api_this"], shell=True)
        if arg2 == "schsheepedule":
            subprocess.Popen(["start", "python", "relive_tv.py", "this"], shell=True)
        logging.info("finish load stream starting killing old live wait 1 min and check live")
        time.sleep(25)
        new_url = f"https://youtube.com/watch?v={live_url}"
        if arg2 == "schedule":
            check_is_live_api(new_url, config.ffmpeg1, "api_this")
        if arg2 == "schsheepedule":
            check_is_live_api(new_url, config.ffmpeg, "this")
        logging.info("killing it rn and the driver and too long and start countdown")
        if arg2 == "schedule":
            subprocess.run(["taskkill", "/f", "/im", config.ffmpeg])
        if arg2 == "schsheepedule":
            subprocess.run(["taskkill", "/f", "/im", config.ffmpeg1])
        time.sleep(2)
        if arg2 == "schedule":
            if config.ytshort == "True":
                subprocess.run([config.ffmpeg, '-fflags', '+genpts', '-re', '-i', 'too-long.mp4', '-c:v', 'h264_qsv', '-c:a', 'aac', '-b:a', '128k', '-preset', 'veryfast', '-filter_complex', '[0:v]scale=1080:600,setsar=1[video];color=black:1080x1920[scaled];[scaled][video]overlay=(main_w-overlay_w)/2:(main_h-overlay_h)/2', '-f', 'flv', f'rtmp://a.rtmp.youtube.com/live2/' + config.rtmp_key], shell=True)
            if config.ytshort == "False":
                subprocess.run([config.ffmpeg, '-re', '-i', 'too-long.mp4', '-c:v', 'libx264', '-preset', 'veryfast', '-c:a', 'aac', '-f', 'flv', f'rtmp://a.rtmp.youtube.com/live2/' + config.rtmp_key], shell=True)
        if arg2 == "schsheepedule":
            if config.ytshort == "True":
                subprocess.run([config.ffmpeg, '-fflags', '+genpts', '-re', '-i', 'too-long.mp4', '-c:v', 'libx264', '-preset', 'veryfast', '-c:a', 'aac', '-filter_complex', '[0:v]scale=1080:600,setsar=1[video];color=black:1080x1920[scaled];[scaled][video]overlay=(main_w-overlay_w)/2:(main_h-overlay_h)/2', '-f', 'flv', f'rtmp://a.rtmp.youtube.com/live2/' + config.rtmp_key_1], shell=True)
            if config.ytshort == "False":
                subprocess.run([config.ffmpeg, '-re', '-i', 'too-long.mp4', '-c:v', 'libx264', '-preset', 'veryfast', '-c:a', 'aac', '-f', 'flv', f'rtmp://a.rtmp.youtube.com/live2/' + config.rtmp_key_1], shell=True)
        logging.info("parting or creating finish")
        return filenametwitch
    except KeyError:
        abc = "abc"
    except Exception as e:
        logging.info(e)
        logging.info("something errorly happen lol stop rn")
        exit()

def fetch_access_token():
        token_response = requests.post(token_url, timeout=15)
        token_response.raise_for_status()
        token = token_response.json()
        return token["access_token"]

######################check_tv###################
if __name__ == "__main__":
    logging.basicConfig(filename="tv.log", level=logging.INFO, format='%(asctime)s %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    logging.getLogger().addHandler(logging.StreamHandler())
    asyncio.run(checkarg())
    exit()
