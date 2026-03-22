from .style import *
from .dataClass import *
from .main import Browser,video_selector,AUTOSELECT,SELECT_MODES,OUTPUTDIR,DEBUGLEVEL

def run(url):
    banner()
    # ── 1. Bolum bilgilerini al ─────────────────────────────
    step(1, 5, "Bolum bilgileri aliniyor...")
    dim("kisa bir sure surucek")
    with Browser() as Pufftr:
        pages = Pufftr.get_serie_info(url)
    success(f"{C.BOLD}{len(pages)}{C.RST} bolum bulundu")
    bar()

    # ── 2. Indirilecek bolumleri sec ────────────────────────
    step(2, 5, "Indirilecek bolumleri sec")
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
    step(3, 5, "Video kaynaklari taraniyor...")
    dim("bir sure surucek")
    with Browser() as Pufftr:
        for i, page in enumerate(page_to_download, 1):
            dim(f"[{i}/{len(page_to_download)}] {page.title}")
            Pufftr.get_videos(page.url, page)
    bar()

    # ── 4. Kaynak secimi ──────────────────────────────────
    step(4, 5, "Kaynak secimi")
    to_download = {}

    def user_selector(page:PageData) -> VideoData:
        pad = max(len(u.translator.name) for u in page.videos)
        return questionary.select(
            f"{page.title}:",
            [questionary.Choice(
                title=f"{u.translator.name.ljust(pad)}  |  {u.name}",
                value=u
            ) for u in page.videos],
            style=Q_STYLE
        ).ask()

    for page in page_to_download:
        if not page.videos:
            warn(f"{page.title} icin video bulunamadi, atlaniyor")
            continue

        selected = None
        if AUTOSELECT:
            selected = video_selector(page.videos, page_to_download, SELECT_MODES)
            if selected:
                success(f"{page.title}: {C.BOLD}{selected.translator.name}{C.RST} | {selected.name} {C.GRAY}(oto){C.RST}")

        if not selected:
            selected = user_selector(page)

        to_download[page] = selected

    if not to_download:
        error("Indirilecek video yok, cikiliyor.")
        exit(0)

    bar()

    # ── 5. Onay & indirme ────────────────────────────────
    step(5, 5, "Onay & indirme")

    def summary():
        pad_title = max(len(p.title) for p in to_download)
        pad_fansub = max(len(v.translator.name) for v in to_download.values())
        print()
        bar("═")
        info(f"{C.BOLD}Indirme Ozeti{C.RST}")
        bar("═")
        for i, (page, video) in enumerate(to_download.items(), 1):
            print(f"  {C.GRAY}{i:3}.{C.RST} {page.title.ljust(pad_title)}  {C.CYAN}{video.translator.name.ljust(pad_fansub)}{C.RST}  |  {video.name}")
        bar()

    summary()

    while True:
        action = questionary.select(
            "",
            [
                questionary.Choice(title="Onayla & indir", value="ok"),
                questionary.Choice(title="Bolum degistir", value="change"),
            ],
            style=Q_STYLE
        ).ask()

        if action == "ok":
            break

        pages_list = list(to_download.keys())
        page_to_change = questionary.select(
            "Hangi bolum?",
            [questionary.Choice(title=p.title, value=p) for p in pages_list],
            style=Q_STYLE
        ).ask()

        new_video = user_selector(page_to_change)
        to_download[page_to_change] = new_video
        summary()

    bar()
    info(f"Indirme basliyor... ({C.BOLD}{len(to_download)}{C.RST} dosya)")
    print()

    with Browser(True) as downloader:
        for i, (page, video) in enumerate(to_download.items(), 1):
            file_name = str(page.title) + ".mp4"
            info(f"[{i}/{len(to_download)}] {C.WHITE}{file_name}{C.RST} {C.GRAY}({video.translator.name} / {video.name}){C.RST}")
            downloader.download(video, str(OUTPUTDIR / file_name))
            success(f"{file_name} tamamlandi")

    print()
    bar("═")
    success(f"{C.BOLD}Tum indirmeler tamamlandi!{C.RST}")
    bar("═")
