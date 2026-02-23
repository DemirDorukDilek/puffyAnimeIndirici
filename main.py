
from playwright.sync_api import sync_playwright,TimeoutError
from bs4 import BeautifulSoup
from datetime import datetime
import questionary
import gdown

BASE_URL = "https://puffytr.com"
LOG_FILE = "error.log"

def log_warn(episode_url, message, **extra):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    details = " | ".join(f"{k}={v}" for k, v in extra.items())
    line = f"[{timestamp}] episode={episode_url} | {message}"
    if details:
        line += f" | {details}"
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")
    print(f"  [WARN] {message}")


def extract_translators(page):
    html = page.content()
    soup = BeautifulSoup(html, "html.parser")

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

    return results, next_ep


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


def resolve_player_location(page, video_url, page_url, episode_url):
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
    return location



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

    
    def get_fileid(self,url,load_time=15,max_fail=15):
        
        try:
            self.page.goto(url, wait_until="domcontentloaded", timeout=load_time*1000)
        except Exception:
            print("[!] Sayfa yukleme timeout, devam ediliyor...")

        page_url = self.page.url
        
        translators, next_episode = extract_translators(self.page)
        print(f"[*] {len(translators)} translator bulundu")
        if next_episode:
            print(f"[*] Sonraki bolum: {next_episode}")

        results = []
        for translator_url, fansub_name in translators:
            print(f"\n[*] Translator: {fansub_name}")

            video_links = fetch_video_links(self.page, translator_url, url)
            print(f"    {len(video_links)} video player bulundu")

            for video_url, video_name in video_links:
                location = resolve_player_location(self.page, video_url, page_url, url)
                if location:
                    results.append((fansub_name, video_name, location))
                    print(f"    [{video_name}] -> {location}")
        
        return results,next_episode
        
            
    def download(self,identifier,file_path,site="GDrive"):
        if site == "GDrive":
            try:
                url = f"https://drive.google.com/file/d/{identifier}/view"
                gdown.download(url=url, output=file_path, quiet=False)
            except:
                self.download_from_drive(identifier,file_path)
        else:
            raise Exception("Unsupported Source")
    
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


url = "https://puffytr.com/dungeon-meshi-23-bolum-izle"
idx = 23 # TODO bolum no cek
url_list = []
while url:
    with Browser() as Anizim:
        urls, next_url = Anizim.get_fileid(url)
    donwload = questionary.select(f"Bolum {idx}: ", choices=[questionary.Choice(title=u, value=u) for u in urls]).ask()
    url_list.append(donwload)
    url = next_url
    idx += 1

with Browser() as downloader:
    for idx,(fansub,player,url) in enumerate(url_list,start=1):
        downloader.download(url,str(idx)+".mp4",player)