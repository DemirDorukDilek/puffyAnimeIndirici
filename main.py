
import gdown
from playwright.sync_api import sync_playwright,TimeoutError


# with sync_playwright() as p:
    
#     def on_request(req):
#         # print(f">> {req.method} {req.url}  type={req.resource_type}")
#         pass
#         # POST body görmek istersen:
#         # if req.method in ("POST", "PUT", "PATCH"):
#         #     print("   post_data:", req.post_data)

#     def on_response(res):
#         req = res.request
#         if "https://drive.google.com/file/d/" in req.url :
#             print(req.url)
#         if "https://puffytr.com/player" in res.url:
#             print(res.url)
#         # print(f"<< {res.status} {req.method} {req.url}")

#     def on_failed(req):
#         pass
#         # print(f"!! FAILED {req.method} {req.url}  failure={req.failure}")
    
#     page = context.new_page()
#     page.on("request", on_request)
#     page.on("response", on_response)
#     page.on("requestfailed", on_failed)
#     def close_new_pages(new_page):
#         if new_page != page:
#             new_page.close()

#     context.on("page", close_new_pages)
    
#     browser = p.chromium.launch(headless=False)
#     context = browser.new_context(record_har_path="network3.har",record_har_content="embed",record_har_mode="full")
    
#     try:
#         page.goto("https://puffytr.com/dungeon-meshi-21-bolum-izle", wait_until="domcontentloaded",timeout=10*1000)
#     except:
#         print("akame")
#         pass
    
#     # page.pause()
#     page.wait_for_timeout(10000)

#     print("finds")
#     page.get_by_role("link", name=" GDrive").click(force=True)
#     print("find")
#     page.wait_for_timeout(1000)
#     print("finds")
#     page.get_by_role("link", name=" GDrive").click(force=True)
#     print("find")
#     page.wait_for_timeout(1000)
#     print("finds")
#     page.get_by_role("link", name=" GDrive").click(force=True)
#     print("find")
#     page.wait_for_timeout(1000)
#     print("finds")
#     page.get_by_role("link", name=" GDrive").click(force=True)
#     print("find")
#     page.wait_for_timeout(1000)
#     print("akame")
#     page.pause()
    
#     # HAR’ın diske yazılması için context'i kapatmak önemli
    
#     context.close()
#     print
#     browser.close()





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
        req = res.request
        if "https://drive.google.com/file/d/" in req.url :
            self.file_id = req.url
        if "https://puffytr.com/player" in res.url:
            print(res.url)

    def on_failed(self,req):
        pass

    
    def get_fileid(self,url,load_time=10,max_fail=15):
        self.file_id = None
        self.page.goto(url, wait_until="domcontentloaded",timeout=load_time*1000)
        self.page.wait_for_timeout(load_time)
        fail = 0
        while self.file_id == None and fail < max_fail:
            try:
                self.page.get_by_role("link", name=" GDrive").click(force=True,timeout=3000)
            except TimeoutError:
                fail += 1
            self.page.wait_for_timeout(1000)
        if fail < max_fail:
            file_id = self.file_id
            self.file_id = None
        else:
            raise TimeoutError
        print(fail)
        try:
            next = self.page.get_by_role("link", name="Sonraki Bölüm ").get_attribute("href")
        except TimeoutError:
            return file_id.split("/")[-2],None
        return file_id.split("/")[-2],next
    
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


url = "https://puffytr.com/dungeon-meshi-24-bolum-final-izle"
idx = 24
while url:
    with Browser() as Anizim:
        file_id,next_url = Anizim.get_fileid(url)
    print(file_id,next_url)
    with Browser(True) as drive:
        drive.download_from_drive(file_id,str(idx)+".mp4")
    idx += 1
    url = next_url