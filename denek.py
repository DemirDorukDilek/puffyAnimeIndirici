from datetime import datetime
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

EPISODE_URL = "https://puffytr.com/dungeon-meshi-21-bolum-izle"
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


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()

    def close_new_pages(new_page):
        if new_page != page:
            new_page.close()
    context.on("page", close_new_pages)

    print(f"[*] Sayfa aciliyor: {EPISODE_URL}")
    try:
        page.goto(EPISODE_URL, wait_until="domcontentloaded", timeout=15000)
    except Exception:
        print("[!] Sayfa yukleme timeout, devam ediliyor...")

    # page.wait_for_timeout(3000)
    page_url = page.url

    translators, next_episode = extract_translators(page)
    print(f"[*] {len(translators)} translator bulundu")
    if next_episode:
        print(f"[*] Sonraki bolum: {next_episode}")

    results = []
    for translator_url, fansub_name in translators:
        print(f"\n[*] Translator: {fansub_name}")

        video_links = fetch_video_links(page, translator_url, EPISODE_URL)
        print(f"    {len(video_links)} video player bulundu")

        for video_url, video_name in video_links:
            location = resolve_player_location(page, video_url, page_url, EPISODE_URL)
            if location:
                results.append((fansub_name, video_name, location))
                print(f"    [{video_name}] -> {location}")

    print("\n" + "=" * 60)
    print("SONUCLAR")
    print("=" * 60)
    for fansub_name, video_name, location in results:
        print(f"  [{fansub_name}] {video_name}: {location}")
    print(f"\nToplam: {len(results)} video location bulundu")
    if next_episode:
        print(f"Sonraki bolum: {next_episode}")

    context.close()
    browser.close()
