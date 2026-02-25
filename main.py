from playwright.sync_api import sync_playwright
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from datetime import datetime
from pathlib import Path
import questionary
import yt_dlp
import gdown
import json
import sys
import os
import re


if not os.path.exists("conf.json"):
    print("conf.json must be in current path")
    exit(1)
with open("conf.json") as f:
    conf = json.load(f)
    
WORKINGDIR = Path(os.getcwd()).expanduser() if conf["WORKINGDIR"] == None else conf["WORKINGDIR"]
OUTPUTDIR = (WORKINGDIR/"out").expanduser() if conf["OUTPUTDIR"] == None else conf["OUTPUTDIR"]
LOGDIR = WORKINGDIR/"log"

WORKINGDIR.mkdir(exist_ok=True)
OUTPUTDIR.mkdir(exist_ok=True)
LOGDIR.mkdir(exist_ok=True)

WARN_LOG_FILE = LOGDIR/"warn.log"
DOWNLOAD_LOG_FILE = LOGDIR/"donwload_error.log"
UNSUPPORTED_PATH = WORKINGDIR/"unsupported"
DEBUGLEVEL = 100

BASE_URL = conf["BASE_URL"]

if os.path.exists(UNSUPPORTED_PATH):
    with open(UNSUPPORTED_PATH,"r") as f:
        UNSUPPORTED = f.readlines()
else:
    UNSUPPORTED = []


class UnLogger:
    def debug(self, msg): pass
    def warning(self, msg): pass
    def error(self, msg): pass

def log_warn(episode_url, message, **extra):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    details = " | ".join(f"{k}={v}" for k, v in extra.items())
    line = f"[{timestamp}] episode={episode_url} | {message}"
    if details:
        line += f" | {details}"
    with open(WARN_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")
    if DEBUGLEVEL < 20: return
    print(f"  [WARN] {message}")

def log_err(file, message, **extra):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    details = " | ".join(f"{k}={v}" for k, v in extra.items())
    line = f"[{timestamp}] {message}"
    if details:
        line += f" | {details}"
    with open(file, "a", encoding="utf-8") as f:
        f.write(line + "\n")
    if DEBUGLEVEL < 10: return
    print(f"  [ERR] {message}")



YDL_OPT = {'simulate': True,'quiet': True,'no_warnings': True, 'logger': UnLogger(),}
YDL_OPT2 = {'format': 'bestvideo+bestaudio/best','outtmpl': None,'merge_output_format': 'mp4','quiet': True,'no_warnings': True}
def check_video(url):
    try:
        with yt_dlp.YoutubeDL(YDL_OPT) as ydl:
            ydl.extract_info(url, download=False)
            return "ok"
    except yt_dlp.utils.DownloadError as e:
        error_msg = str(e).lower()
        if any(kw in error_msg for kw in ['too many', 'quota', '403', 'forbidden']):
            status = 'quota'
        elif any(kw in error_msg for kw in ['removed', 'deleted', 'not found', '404', 'unavailable']):
            status = 'removed'
        elif any(kw in error_msg for kw in ['unsupported', 'no suitable', 'not supported', 'no longer supported']):
            domain = urlparse(url).netloc
            if domain not in UNSUPPORTED:
                with open(UNSUPPORTED_PATH, "a", encoding="utf-8") as f:
                    f.write(domain + "\n")
                UNSUPPORTED.append(domain)
            status = 'unsupported'
        elif any(kw in error_msg for kw in ['timed out', 'unreachable', 'connection reset by peer']):
            status = 'timedout'
        else:
            log_err(DOWNLOAD_LOG_FILE,f"Error at: {url} with {error_msg}")
            status = 'error'
        return status

def extract_translators(page):
    html = page.content()
    soup = BeautifulSoup(html, "html.parser")

    episode_title = None
    title_tag = soup.find("h1", class_="anizm_pageTitle")
    if title_tag:
        span = title_tag.find("span")
        if span:
            raw = span.get_text(strip=True).lstrip("/ ").strip()
            episode_title = re.sub(r'[\\/*?:"<>|\ ]', '_', raw)

    results = []
    for container in soup.find_all("div", class_="fansubSecimKutucugu"):
        for link in container.find_all("a", attrs={"translator": True}):
            translator_url = link.get("translator")
            fansub_name = link.get("data-fansub-name", "Unknown")
            if translator_url:
                results.append((translator_url, fansub_name))

    next_ep = None
    for a in soup.find_all("a", class_="puf_02"):
        if "Sonraki" in a.get_text():
            next_ep = a.get("href")
            break

    return results, next_ep, episode_title


def fetch_video_links(page, translator_url, episode_url):
    resp = page.request.get(translator_url)
    if resp.status != 200:
        log_warn(episode_url, "Translator request failed", translator_url=translator_url, status=resp.status)
        return []

    data = resp.json()
    if data.get("status") != "success":
        log_warn(episode_url, "API status basarisiz", translator_url=translator_url, api_status=data.get("status"))
        return []

    html_content = data.get("data", "")
    if not html_content:
        log_warn(episode_url, "data key bos veya yok", translator_url=translator_url)
        return []

    soup = BeautifulSoup(html_content, "html.parser")
    results = []
    for link in soup.find_all("a", attrs={"video": True}):
        video_url = link.get("video")
        video_name = link.get("data-video-name", "Unknown")
        if video_url:
            results.append((video_url, video_name))
    return results


def resolve_player_location(page, video_url, page_url, episode_url, video_name):
    player_url = video_url.replace("/video/", "/player/")
    try:
        resp = page.request.get(player_url, max_redirects=0, headers={
            "Referer": page_url,
            "Origin": BASE_URL,
        })
    except Exception as e:
        log_warn(episode_url, "Player request failed", player_url=player_url, error=str(e))
        return None

    location = resp.headers.get("location")
    if not location:
        log_warn(episode_url, "Location header yok", player_url=player_url, status=resp.status)
    
    if urlparse(location).netloc not in UNSUPPORTED:
        stat = check_video(location)
        if stat == "ok" or stat == "quota" and video_name == "GDrive":
            return location
    return None



class Browser:
    def __init__(self,accept_downloads=False):
        self._pw = sync_playwright().start()
        self.browser = self._pw.chromium.launch(headless=True)
        self.context = self.browser.new_context(record_har_path="network3.har",record_har_content="embed",record_har_mode="full",accept_downloads=accept_downloads)
        self.page = self.context.new_page()
        
        self.page.on("request", self.on_request)
        self.page.on("response", self.on_response)
        self.page.on("requestfailed", self.on_failed)
        self.context.on("page", self.close_new_pages)
        
        self.last_uuid = None

    def close_new_pages(self,new_page):
        if new_page != self.page:
            new_page.close()

    def on_request(self,req):
        pass
    def on_response(self,res):
        pass
    def on_failed(self,req):
        pass

    
    def get_videos(self,url,load_time=15):
        
        try:
            self.page.goto(url, wait_until="domcontentloaded", timeout=load_time*1000)
        except Exception:
            print("[!] Sayfa yukleme timeout, devam ediliyor...")

        page_url = self.page.url
        
        translators, next_episode, episode_title = extract_translators(self.page)
        print(f"[*] {len(translators)} translator bulundu")
        if episode_title:
            print(f"[*] Bolum adi: {episode_title}")
        if next_episode:
            print(f"[*] Sonraki bolum: {next_episode}")

        results = []
        for translator_url, fansub_name in translators:
            print(f"\n[*] Translator: {fansub_name}")

            video_links = fetch_video_links(self.page, translator_url, url)
            print(f"    {len(video_links)} video player bulundu")

            for video_url, video_name in video_links:
                location = resolve_player_location(self.page, video_url, page_url, url, video_name)
                if location:
                    results.append((fansub_name, video_name, location))
                    print(f"    [{video_name}] -> {location}")
        
        return results, next_episode, episode_title
        
            
    def download(self,identifier,file_path,site="GDrive"):
        if site == "GDrive":
            try:
                url = f"https://drive.google.com/file/d/{identifier}/view"
                gdown.download(url=url, output=file_path, quiet=False)
            except:
                self.download_from_drive(identifier,file_path)
        else:
            YDL_OPT2["outtmpl"] = file_path
            try:
                with yt_dlp.YoutubeDL(YDL_OPT2) as ydl:
                    ydl.download([identifier])
            except Exception:
                log_err(DOWNLOAD_LOG_FILE,f"unable to donwload valid url: {identifier}")
            YDL_OPT2["outtmpl"] = None
            
    def download_from_drive(self, file_id, file_path):
        url = f"https://drive.google.com/uc?export=download&id={file_id}"

        self.page.goto(url, wait_until="domcontentloaded")
        form = self.page.locator("form#download-form")

        with self.page.expect_download(timeout=120_000) as dl:
            if form.count() > 0:
                form.evaluate("form => form.submit()")
            else:
                self.page.goto(url)

        dl.value.save_as(file_path)

    def close(self):
        self.browser.close()
        self._pw.stop()
    
    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

class Ep:
    def __init__(self,videos,ep_title):
        self.videos = videos
        self.ep_title = ep_title

if DEBUGLEVEL > 0:
    url = "https://puffytr.com/dungeon-meshi-24-bolum-final-izle"
else:
    if sys.argv[1] == "-conf":
        exec("nano conf.json")
        exit(0)
    url = sys.argv[1]
    
url_list = []
with Browser() as Anizim:
    while url:
        urls, next_url,ep_title = Anizim.get_videos(url)
        url_list.append(Ep(urls,ep_title))
        url = next_url

to_download = []
for ep in url_list:
    donwload = questionary.select(f"{ep.ep_title}: ", choices=[questionary.Choice(title=u, value=u) for u in ep.videos]).ask()
    to_download.append((ep_title,donwload))

with Browser() as downloader:
    for ep_title,(fansub,player,url) in to_download:
        downloader.download(url,str(OUTPUTDIR/(str(ep_title)+".mp4")),player)