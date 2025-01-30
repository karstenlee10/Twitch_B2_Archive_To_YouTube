import subprocess
import sys
import os
import time
import logging
from selenium import webdriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.remote.file_detector import LocalFileDetector
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import NoSuchElementException, ElementNotInteractableException, SessionNotCreatedException
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.protobuf.timestamp_pb2 import Timestamp
from google.oauth2 import service_account
import google.auth.exceptions
import config_tv as config
import psutil
import requests
import enum
import unicodedata
import string
import random
from datetime import datetime, timedelta
import streamlink
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from requests.exceptions import RequestException
import json
import threading
import getopt
import re
import shutil
from twitchAPI.twitch import Twitch
from twitchAPI.type import AuthScope
import asyncio

t = time.localtime()
current_time = time.strftime("%H:%M:%S", t)
refresh = 15
token_url = f"https://id.twitch.tv/oauth2/token?client_id={config.client_id}&client_secret={config.client_secret}&grant_type=client_credentials"
APP_TOKEN_FILE = "client_secret.json"
USER_TOKEN_FILE = "user_token.json"
SCOPES = [
    'https://www.googleapis.com/auth/youtube.force-ssl',
    'https://www.googleapis.com/auth/userinfo.profile',
    'https://www.googleapis.com/auth/gmail.readonly',
]
home_dir = os.path.expanduser("~")
arguments = sys.argv
desired_url = "https://www.twitch.tv/" + config.username
bilibili_desired_url = "https://live.bilibili.com/" + config.username

def find_gmail_title(title):
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

def offline_check(driver, live_url, spare_link, important, titleforgmail):
    logging.info("Starting offline detection monitoring...")
    refresh_count = 0
    countdownhours = 0
    numberpart = 0
    fewtimes = 0
    gmailcount = 0
    
    # Create event loop and run async code
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    async def check_offline():
        # Move all nonlocal declarations to the start of the function
        nonlocal refresh_count, countdownhours, numberpart, fewtimes, gmailcount, titleforgmail
        
        twitch = await Twitch(config.client_id, config.client_secret)
        await twitch.authenticate_app([])
        
        while True:
            try:
                if config.Twitch == "True":
                    streams = []
                    async for stream in twitch.get_streams(user_login=[config.username]):
                        streams.append(stream)
                    
                    if not streams:
                        fewtimes += 1
                        if fewtimes == 2:
                            logging.info("Stream offline detected. Shutting down...")
                            if config.unliststream == "True":
                                logging.info("public back the stream")
                                public_stream(live_url)
                            subprocess.run(["taskkill", "/f", "/im", config.apiexe])
                            subprocess.Popen(["start", "python", "check_tv.py", spare_link, important], shell=True)
                            return
                
                if config.BiliBili == "True":
                    try:
                        response = requests.get(f"https://live.bilibili.com/{config.username}")
                        soup = BeautifulSoup(response.text, 'html.parser')
                        soup.find("div", {"class": "web-player-ending-panel"})
                        fewtimes += 1
                        if fewtimes == 6:
                            logging.info("Stream offline detected. Reloading program...")
                            if config.unliststream == "True":
                                logging.info("public back the stream")
                                public_stream(live_url)
                            subprocess.run(["taskkill", "/f", "/im", config.apiexe])
                            subprocess.Popen(["start", "python", "check_tv.py", spare_link, important], shell=True)
                            exit()
                    except Exception as e:
                        logging.error(f"Error checking BiliBili stream: {e}")
                        pass

                # Keep existing refresh and countdown logic
                refresh_count += 1
                countdownhours += 1
                gmailcount += 1

                # Keep existing Gmail check logic
                if gmailcount == 11:
                    whatistheans = find_gmail_title(titleforgmail)
                    if whatistheans == "True":
                        logging.info("alert detect third party info restart stream to spare stream")
                        subprocess.run(["taskkill", "/f", "/im", config.apiexe])
                        titleforgmail = checktitlelol(numberpart, important, "Null", spare_link)
                        logging.info("finish reloading start spare stream")
                        logging.info("load spare stream")
                        if important == "schedule":
                            important = "schsheepedule"
                        elif important == "schsheepedule":
                            important = "schedule"
                        live_spare_url = checktitlelol("0", important, "True", "Null")
                        subprocess.Popen(["start", config.apiexe], shell=True)
                        if config.unliststream == "True":
                            logging.info("public back the stream")
                            public_stream(live_url)
                        logging.info("load offline_check again")
                        numberpart += 1
                        live_url = spare_link
                        spare_link = live_spare_url
                        logging.info(important)
                        countdownhours = 0
                        gmailcount = 0
                    else:
                        gmailcount = 0

                if refresh_count == 60:
                    if config.BiliBili == "True":
                        driver.refresh()
                        await asyncio.sleep(7)
                        refresh_count = 0
                
                if countdownhours == 7871:
                    logging.info("12 hour limit reached. Reloading stream...")
                    subprocess.run(["taskkill", "/f", "/im", config.apiexe])
                    titleforgmail = checktitlelol(numberpart, important, "Null", spare_link)
                    logging.info("finish reloading start spare stream")
                    logging.info("load spare stream")
                    if important == "schedule":
                        important = "schsheepedule"
                    elif important == "schsheepedule":
                        important = "schedule"
                    live_spare_url = checktitlelol("0", important, "True", "Null")
                    subprocess.Popen(["start", config.apiexe], shell=True)
                    if config.unliststream == "True":
                        logging.info("public back the stream")
                        public_stream(live_url)
                    logging.info("load offline_check again")
                    numberpart += 1
                    live_url = spare_link
                    spare_link = live_spare_url
                    logging.info(important)
                    countdownhours = 0

                await asyncio.sleep(15)  # Changed to asyncio.sleep
                
            except Exception as e:
                logging.error(f"Error in offline check: {e}")
                await asyncio.sleep(5)  # Changed to asyncio.sleep
    
    # Run the async function
    loop.run_until_complete(check_offline())
    loop.close()

async def get_twitch_client():
    twitch = await Twitch(config.client_id, config.client_secret)
    await twitch.authenticate_app([])
    return twitch

def load_check(driver):
    logging.info("Waiting for stream to go live...")
    while True:
        try:
            if config.Twitch == "True":
                # Create event loop and run async code
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                async def check_stream():
                    twitch = await Twitch(config.client_id, config.client_secret)
                    await twitch.authenticate_app([])
                    logging.info(f"Checking Twitch stream status for user: {config.username}")
                    
                    while True:
                        streams = []
                        async for stream in twitch.get_streams(user_login=[config.username]):
                            streams.append(stream)
                        
                        if not streams:
                            logging.info(f"No live stream data found for {config.username}")
                            await asyncio.sleep(5)
                        else:
                            return streams
                
                # Run the async function and get results
                streams = loop.run_until_complete(check_stream())
                loop.close()
                
                if streams:
                    stream = streams[0]
                    logging.info(f"Stream is now live! Title: {stream.title}")
                    break
            
            if config.BiliBili == "True":
                logging.info("Checking BiliBili stream status...")
                element = driver.find_element("xpath", "//div[@class='web-player-ending-panel']")
                logging.info("Stream is now live!")
                break

        except NoSuchElementException:
            logging.info("Stream element not found, waiting...")
            time.sleep(5)  # This is fine as it's not in async context
        except Exception as e:
            logging.error(f"Error checking stream status: {str(e)}")
            if config.BiliBili == "True":
                logging.info("Browser session crashed - restarting driver...")
                try:
                    driver.quit()
                except:
                    abc = "abc"
                driveromg = selreload()
                load_check(driveromg)

def selreload():
        logging.info("Initializing new browser session...")
        if config.BiliBili == "True":
            driver = webdriver.Chrome()
            logging.info(f"Navigating to BiliBili channel: {config.username}")
            driver.get(f"https://live.bilibili.com/{config.username}")
        time.sleep(7)
        if config.BiliBili == "True":
              return driver

def selwebdriver_check(yt_link, infomation, driver):
      try:
        if driver == "Null":
          if yt_link == "Null":
             haha = "schsheepedule"
             live_url = checktitlelol("0", haha, "True", "Null")
          else:
             live_url = yt_link
             haha = infomation
          if config.Twitch == "True":
              driver = "Null"
          if config.BiliBili == "True":
            driver = webdriver.Chrome()
            driver.get(f"https://live.bilibili.com/{config.username}")
          time.sleep(7)
        if config.BiliBili == "True":
         try:
           live_link = f"https://live.bilibili.com/{config.username}"
           driver.find_element("xpath", "//div[@class='web-player-ending-panel']")
           logging.info("wait stream to start")
           load_check(driver)
           logging.info("load start")
           start_check(driver, live_url, haha)
         except NoSuchElementException:
           logging.info("load start immdently")
           start_check(driver, live_url, haha)
        if config.Twitch == "True":
           load_check("Null")
           logging.info("load start")
           start_check(driver, live_url, haha)
      except Exception as e:
            logging.info(e)
            logging.info("the script failed shuting down")

def checkarg():
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
      selwebdriver_check(arg1, arg2, "Null")
      exit()
    except Exception as e:
          logging.error(f"Script failed to execute: {e}")
          logging.info("failed script shutdown")
  except Exception as e:
   try:
    logging.info("theres no arg")
    arg = "Null"
    selwebdriver_check(arg, arg, "Null")
   except Exception as e:
          logging.error(f"Failed to execute with null args: {e}")
          logging.info("failed script shutdown")

def start_check(driver, live_url, haha):
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
              titleforgmail = selwebdriver(live_url, haha)
            except UnboundLocalError:
                  this_bug_is_unfixable = "sigh"
            logging.info("load spare stream")
            live_spare_url = checktitlelol("0", inport, "True", "Null")
            logging.info("wait for offine now... and start countdown")
            try:
               offline_check(driver, live_url, live_spare_url, inport, titleforgmail)
            except:
              logging.info("driver shutdown restarting")
              try:
                driver.quit()
              except:
                abc = "abc"
              driveromg = selreload()
              offline_check(driveromg, live_url, live_spare_url, inport, titleforgmail)
            exit()

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

    if os.path.exists(USER_TOKEN_FILE):
      try:
        creds = Credentials.from_authorized_user_file(USER_TOKEN_FILE, SCOPES)
      except json.JSONDecodeError:
          pass
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(APP_TOKEN_FILE, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(USER_TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
    service = build('youtube', 'v3', credentials=creds)
    return service

def get_gmail_service():
    creds = None

    if os.path.exists(USER_TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(USER_TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(APP_TOKEN_FILE, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(USER_TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
    service = build('gmail', 'v1', credentials=creds)
    return service

def get_yt_title():
 while True:
   service = get_service()
   request = service.search().list(
       part="snippet",
       channelId=config.username,
       eventType="live",
       type="video"
   )

   response = request.execute()

   if "items" in response and len(response["items"]) > 0:
       live_stream = response["items"][0]
       video_id = live_stream["id"]["videoId"]
       video_title = live_stream["snippet"]["title"]
       logging.info(f"The channel is currently live. Video Title: {video_title}, Video ID: {video_id}")
       return video_title, video_id
   else:
       time.sleep(5)

def edit_live_stream(video_id, new_title, new_description):
  while True:
    try:
       service = get_service()
       category_id = '24'
       request = service.videos().update(
             part="snippet",
             body={
                 "id": video_id,
                 "snippet": {
                     "title": new_title,
                     "description": new_description,
                     "categoryId": category_id
            }
        }
    )
       response = request.execute()
       return response['id']
       break
    except google.auth.exceptions.RefreshError as e:
      logging.info(f"Error: {e}")
      logging.info("error edit token bad reget token")
      subprocess.run(["python", "get_token.py"], shell=True)
      time.sleep(5)

def public_stream(live_id):
  while True:
    try:
       service = get_service()
       scheduled_start_time = datetime.utcnow().isoformat()
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
    except google.auth.exceptions.RefreshError as e:
      logging.info(f"Error: {e}")
      logging.info("error token bad reget token")
      subprocess.run(["python", "get_token.py"], shell=True)
      time.sleep(5)

def create_live_stream(title, description, kmself):
  while True:
    try:
       service = get_service()
       scheduled_start_time = datetime.utcnow().isoformat()
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
                    "lifeCycleStatus": "ready",
                    "recordingStatus": "notRecording",
                    "selfDeclaredMadeForKids": False
                },
                "contentDetails": {
                    "enableAutoStart": True,
                    "enableAutoStop": True,
                    "latencyPreference": "ultraLow"
                }
            }
        )
       response = request.execute()
       return response['id']
       break
    except google.auth.exceptions.RefreshError as e:
      logging.info(f"Error: {e}")
      logging.info("error token bad reget token")
      subprocess.run(["python", "get_token.py"], shell=True)
      time.sleep(5)

def api_load(url):
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
      nameofaccount = f"//div[contains(text(),'{config.accountname}')]"
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

def get_stream_linkandtitle():
      response = requests.get(f"https://live.bilibili.com/{config.username}")
      soup = BeautifulSoup(response.text, 'html.parser')
      title = soup.title.string
      return re.sub(r' - .*', '', title)

def selwebdriver(live_url, timeisshit):
      if config.Twitch == "True":
       url = "https://api.twitch.tv/helix/streams"
       access_token = fetch_access_token()
       info = None
       status = TwitchResponseStatus.ERROR
       try:
            headers = {"Client-ID": config.client_id, "Authorization": "Bearer " + access_token}
            r = requests.get(url + "?user_login=" + config.username , headers=headers, timeout=15)
            r.raise_for_status()
            info = r.json()
            if info is None or not info["data"]:
                status = TwitchResponseStatus.OFFLINE
            else:
                status = TwitchResponseStatus.ONLINE
       except requests.exceptions.RequestException as e:
            if e.response:
                if e.response.status_code == 401:
                    status = TwitchResponseStatus.UNAUTHORIZED
                if e.response.status_code == 404:
                    status = TwitchResponseStatus.NOT_FOUND
       try:
        channels = info["data"]
        channel = next(iter(channels), None)
        titletv = channel.get('title')
       except AttributeError:
            logging.info('the stream is not live please start at relive_tv.py first! try again')
            time.sleep(5)
            selwebdriver(live_url, timeisshit)
      if config.BiliBili == "True":
            titletv = get_stream_linkandtitle()
      textnoemo = ''.join('' if unicodedata.category(c) == 'So' else c for c in titletv)
      if "<" in textnoemo or ">" in textnoemo:
                   textnoemo = textnoemo.replace("<", "").replace(">", "")
      characters = string.ascii_letters + string.digits
      random_string = ''.join(random.choices(characters, k=7))
      filenametwitch = config.username +  " | " + textnoemo +  " | " + datetime.now() \
                    .strftime("%Y-%m-%d")
      if config.Twitch == "True":
              deik = f"this stream is from https://twitch.tv/{config.username} (Stream Name:{textnoemo})"
      if config.BiliBili == "True":
              deik = f"this stream is from https://live.bilibili.com/{config.username} (Stream Name:{textnoemo})"
      if len(filenametwitch) > 100:
              logging.info("title too long")
              filenametwitch = config.username +  " | " + datetime.now() \
                    .strftime("%Y-%m-%d") + " | " + random_string
      logging.info('process of edit name started')
      try:
            edit_live_stream(live_url, filenametwitch, deik)
            new_url = f"https://youtube.com/watch?v={live_url}"
            logging.info("wait to check live 40sec")
            time.sleep(40)
            if timeisshit == "schedule":
              check_is_live_api(new_url, config.ffmpeg1, "api_this")
            if timeisshit == "schsheepedule":
              check_is_live_api(new_url, config.ffmpeg, "this")
      finally:
            logging.info('edit finished contiue the stream')
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
                  subprocess.run(["taskkill", "/f", "/im", ffmpeg])
                  subprocess.Popen(["start", "python", "relive_tv.py", text], shell=True)
                  exit()
def checktitlelol(arg1, arg2, reload, live_url):
      if config.Twitch == "True" and reload == "Null":
            max_retries = 3
            retry_count = 0
            
            while retry_count < max_retries:
                try:
                    titletv = get_twitch_stream_title()
                    if not titletv:
                        status = TwitchResponseStatus.OFFLINE
                        logging.info("Stream appears to be offline, retrying...")
                    else:
                        status = TwitchResponseStatus.ONLINE
                        textnoemo = ''.join('[EMOJI]' if unicodedata.category(c) == 'So' else c for c in titletv)
                        if "<" in textnoemo or ">" in textnoemo:
                            textnoemo = textnoemo.replace("<", "[ERROR]").replace(">", "[ERROR]")
                        calit = int(arg1) + 1
                        filenametwitch = config.username + " | " + textnoemo + " | " + datetime.now() \
                            .strftime("%Y-%m-%d") + " | " + "part " + str(calit)
                        if len(filenametwitch) > 100:
                            filenametwitch = config.username + " | " + datetime.now() \
                                .strftime("%Y-%m-%d") + " | " + "part " + str(calit)
                        deik = f"this stream is from twitch.tv/{config.username} (Stream Name:{textnoemo})"
                        break  # Success - exit the retry loop
                        
                except Exception as e:
                    retry_count += 1
                    logging.error(f"Error getting Twitch stream title (attempt {retry_count}/{max_retries}): {e}")
                    if retry_count >= max_retries:
                        status = TwitchResponseStatus.ERROR
                        logging.error("Max retries reached, using fallback title")
                        # Use a fallback title if all retries fail
                        filenametwitch = f"{config.username} | Stream | {datetime.now().strftime('%Y-%m-%d')}"
                        deik = f"this stream is from twitch.tv/{config.username}"
                    else:
                        time.sleep(2)  # Wait before retrying

      if config.BiliBili == "True" and reload == "Null":
          titletv = get_stream_linkandtitle()
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

def get_twitch_stream_title():
    # Create event loop and run async code
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    async def get_stream_info():
        twitch = await Twitch(config.client_id, config.client_secret)
        await twitch.authenticate_app([])
        streams = []
        async for stream in twitch.get_streams(user_login=[config.username]):
            streams.append(stream)
        return streams
    
    try:
        streams = loop.run_until_complete(get_stream_info())
        loop.close()
        
        if streams:
            return streams[0].title
        return None
    except Exception as e:
        logging.error(f"Error getting Twitch stream info: {e}")
        return None

######################check_tv##################
if __name__ == "__main__":
    logging.basicConfig(filename="tv.log", level=logging.INFO, format='%(asctime)s %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    logging.getLogger().addHandler(logging.StreamHandler())
    from google_auth_oauthlib.flow import InstalledAppFlow
    checkarg()
    exit()
