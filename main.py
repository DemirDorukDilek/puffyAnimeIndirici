from playwright.sync_api import sync_playwright,Page
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from datetime import datetime
from pathlib import Path
import questionary
import yt_dlp
import json
import sys
import os
import re

from dataClass import *
from style import *

if not os.path.exists("conf.json"):
    print("conf.json must be in current path")
    exit(1)
with open("conf.json") as f:
    conf = json.load(f)
    
WORKINGDIR = Path(os.getcwd()).expanduser() if conf["WORKINGDIR"] == None else Path(conf["WORKINGDIR"])
OUTPUTDIR = (WORKINGDIR/"out").expanduser() if conf["OUTPUTDIR"] == None else Path(conf["OUTPUTDIR"])
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
        UNSUPPORTED = f.read().split()
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
    warn(message)

def log_err(file, message, **extra):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    details = " | ".join(f"{k}={v}" for k, v in extra.items())
    line = f"[{timestamp}] {message}"
    if details:
        line += f" | {details}"
    with open(file, "a", encoding="utf-8") as f:
        f.write(line + "\n")
    if DEBUGLEVEL < 10: return
    error(message)



YDL_OPT = {'simulate': True,'quiet': True,'no_warnings': True, 'logger': UnLogger(),}
YDL_OPT2 = {
    'format': 'source/bestvideo+bestaudio/best',
    'outtmpl': None,
    'merge_output_format': 'mp4',
    'remux_video': 'mp4',
    'quiet': True,
    'no_warnings': True,
    'external_downloader': 'aria2c',
    'external_downloader_args': ['--min-split-size=1M', '--max-connection-per-server=16', '--split=16'],
    'logger': UnLogger(),
}
def check_video(url:str) -> str:
    try:
        with yt_dlp.YoutubeDL(YDL_OPT) as ydl:
            ydl.extract_info(url, download=False)
            return "ok"
    except yt_dlp.utils.DownloadError as e:
        error_msg = str(e).lower()
        if any(kw in error_msg for kw in ['too many', 'quota']):
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

def fetch_page_data(page:Page,url:str) -> PageData:
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=15*1000)
    except Exception as e:
        warn("Sayfa yukleme timeout, devam ediliyor...")
    html = page.content()
    soup = BeautifulSoup(html, "html.parser")

    episode_title = None
    title_tag = soup.find("h1", class_="anizm_pageTitle")
    if title_tag:
        span = title_tag.find("span")
        if span:
            raw = span.get_text(strip=True).lstrip("/ ").strip()
            episode_title = re.sub(r'[\\/*?:"<>|\ ]', '_', raw)

    
    translators = []
    for container in soup.find_all("div", class_="fansubSecimKutucugu"):
        for link in container.find_all("a", attrs={"translator": True}):
            translator = Translator(link.get("data-fansub-name", "Unknown"), link.get("translator"))
            if translator.url:
                translators.append(translator)

    next_ep = None
    for a in soup.find_all("a", class_="puf_02"):
        if "Sonraki" in a.get_text():
            next_ep = a.get("href")
            break
    
    return PageData(episode_title,url,next_ep,translators,[])


def fetch_video_links(page:Page, translator:Translator, episode_url:str) -> List[VideoData]:
    resp = page.request.get(translator.url)
    if resp.status != 200:
        log_warn(episode_url, "Translator request failed", translator_url=translator.url, status=resp.status)
        return []

    data = resp.json()
    if data.get("status") != "success":
        log_warn(episode_url, "API status basarisiz", translator_url=translator.url, api_status=data.get("status"))
        return []

    html_content = data.get("data", "")
    if not html_content:
        log_warn(episode_url, "data key bos veya yok", translator_url=translator.url)
        return []

    soup = BeautifulSoup(html_content, "html.parser")
    videos = []
    for link in soup.find_all("a", attrs={"video": True}):
        video = VideoData(link.get("data-video-name", "Unknown"),link.get("video").replace("/video/", "/player/"),None,"Unknown",translator)
        if video.site_url:
            videos.append(video)
    return videos


def resolve_player_location(page:Page, video:VideoData, page_url:str, episode_url:str) -> bool:
    try:
        resp = page.request.get(video.site_url, max_redirects=0, headers={
            "Referer": page_url,
            "Origin": BASE_URL,
        })
    except Exception as e:
        log_warn(episode_url, "Player request failed", player_url=video.site_url, error=str(e))
        return None

    video.real_url = resp.headers.get("location")
    
    if not video.real_url:
        log_warn(episode_url, "Location header yok", player_url=video.site_url, status=resp.status)
    
    if urlparse(video.real_url).netloc not in UNSUPPORTED:
        video.stat = check_video(video.real_url)
        if video.stat == "ok" or (video.stat == "quota" and video.name == "GDrive"):
            return True
    return False



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

    def get_serie_info(self,url:str,load_time:int=15) -> List[PageData]:
        try:
            self.page.goto(url, wait_until="domcontentloaded", timeout=load_time*1000)
        except Exception:
            warn("Sayfa yukleme timeout, devam ediliyor...")
            
        page_datas = []
        next_url = url
        while next_url:
            page = fetch_page_data(self.page,next_url)
            page_datas.append(page)
            next_url = page.next_page
        
        return page_datas
    
    
    def get_videos(self,url:str,page:PageData,load_time:int=15) -> None:
        info(f"{C.WHITE}{page.title}{C.RST} icin video verileri aliniyor...")
        try:
            self.page.goto(url, wait_until="domcontentloaded", timeout=load_time*1000)
        except Exception:
            warn("Sayfa yukleme timeout, devam ediliyor...")

        page_url = self.page.url


        valid_videos = []
        for translator in page.translators:
            videos = fetch_video_links(self.page, translator, url)
            if videos:
                success(f"{translator.name}: {C.BOLD}{len(videos)}{C.RST} player bulundu")
            else:
                dim(f"{translator.name}: player bulunamadi")

            for video in videos:
                if resolve_player_location(self.page, video, page_url, url):
                    valid_videos.append(video)

        page.videos.extend(valid_videos)
        
            
    def download(self,video:VideoData,file_path:str) -> None:
        YDL_OPT2["outtmpl"] = file_path
        try:
            if video.stat == "ok":
                with yt_dlp.YoutubeDL(YDL_OPT2) as ydl:
                    ydl.download([video.real_url])
            elif video.name == "GDrive" and video.stat == "quota":
                self.download_from_drive(video.real_url,file_path)
            else:
                raise Exception(f"Unvalid status at: {video.real_url} {video.stat}")
                
        except Exception as e:
            log_err(DOWNLOAD_LOG_FILE,f"unable to donwload valid url: {video.real_url} {video.stat}")

        YDL_OPT2["outtmpl"] = None
            
    def download_from_drive(self, identifier, file_path):
        file_id = identifier.split("/")[-2]
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


if DEBUGLEVEL > 0:
    url = "https://puffytr.com/takopii-no-genzai-5-bolum-izle"
else:
    if sys.argv[1] == "-conf":
        os.system("nano conf.json")
        exit(0)
    url = sys.argv[1]

banner()

# ── 1. Bolum bilgilerini al ─────────────────────────────
step(1, 4, "Bolum bilgileri aliniyor...")
dim("kisa bir sure surucek")
with Browser() as Anizim:
    pages = Anizim.get_serie_info(url)
success(f"{C.BOLD}{len(pages)}{C.RST} bolum bulundu")
bar()

# ── 2. Indirilecek bolumleri sec ────────────────────────
step(2, 4, "Indirilecek bolumleri sec")
page_to_download = questionary.checkbox(
    "",
    [questionary.Choice(title=f"{page.title}", value=page) for page in pages],
    instruction='("space" -> sec, "a" -> hepsini sec, "i" -> ters cevir)',
    style=Q_STYLE
).ask()

if not page_to_download:
    warn("Hicbir bolum secilmedi, cikiliyor.")
    exit(0)

info(f"{C.BOLD}{len(page_to_download)}{C.RST} bolum secildi")
bar()

# ── 3. Video kaynaklarini tara ──────────────────────────
step(3, 4, "Video kaynaklari taraniyor...")
dim("bir sure surucek")
with Browser() as Anizim:
    for i, page in enumerate(page_to_download, 1):
        dim(f"[{i}/{len(page_to_download)}] {page.title}")
        Anizim.get_videos(page.url, page)
bar()

# ── 4. Kaynak sec & indir ──────────────────────────────
step(4, 4, "Kaynak secimi & indirme")
to_download = []
for page in page_to_download:
    if len(page.videos):
        pad = max(len(u.translator.name) for u in page.videos)
        donwload = questionary.select(f"{page.title}:",[questionary.Choice(title=f"{u.translator.name.ljust(pad)}  |  {u.name}",value=u) for u in page.videos], style=Q_STYLE).ask()
        to_download.append((page, donwload))
    else:
        warn(f"{page.title} icin video bulunamadi, atlaniyor")

if not to_download:
    error("Indirilecek video yok, cikiliyor.")
    exit(0)

bar()
info(f"Indirme basliyor... ({C.BOLD}{len(to_download)}{C.RST} dosya)")
print()

with Browser(True) as downloader:
    for i, (page, video) in enumerate(to_download, 1):
        file_name = str(page.title) + ".mp4"
        info(f"[{i}/{len(to_download)}] {C.WHITE}{file_name}{C.RST} {C.GRAY}({video.translator.name} / {video.name}){C.RST}")
        downloader.download(video, str(OUTPUTDIR / file_name), video.name)
        success(f"{file_name} tamamlandi")

print()
bar("═")
success(f"{C.BOLD}Tum indirmeler tamamlandi!{C.RST}")
bar("═")







