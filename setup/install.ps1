# AnimeDownloader Kurulum Scripti (Windows)
# Calistirmak icin: powershell -ExecutionPolicy Bypass -File install.ps1

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "  +----------------------------------------------+" -ForegroundColor Cyan
Write-Host "  |    A N I M E  D O W N L O A D E R           |" -ForegroundColor Cyan
Write-Host "  |             K U R U L U M                    |" -ForegroundColor Cyan
Write-Host "  +----------------------------------------------+" -ForegroundColor Cyan
Write-Host ""

# Python kontrolu
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "  [X] Python bulunamadi." -ForegroundColor Red
    Write-Host "  Lutfen https://www.python.org adresinden Python 3.10+ kurun." -ForegroundColor Yellow
    Write-Host "  Kurulum sirasinda 'Add Python to PATH' secenegini isaretleyin!" -ForegroundColor Yellow
    exit 1
}

$pyver = python -c "import sys; print(sys.version_info.minor)"
if ([int]$pyver -lt 10) {
    Write-Host "  [X] Python 3.10 veya uzeri gerekli." -ForegroundColor Red
    exit 1
}
Write-Host "  [*] Python kontrolu OK" -ForegroundColor Green

# aria2c kontrolu
if (-not (Get-Command aria2c -ErrorAction SilentlyContinue)) {
    Write-Host "  [*] aria2c bulunamadi, yukleniyor..." -ForegroundColor Yellow

    if (Get-Command winget -ErrorAction SilentlyContinue) {
        winget install --id aria2.aria2 -e --silent
    } elseif (Get-Command choco -ErrorAction SilentlyContinue) {
        choco install aria2 -y
    } elseif (Get-Command scoop -ErrorAction SilentlyContinue) {
        scoop install aria2
    } else {
        Write-Host "  [X] aria2c otomatik yuklenemedi." -ForegroundColor Red
        Write-Host "  Lutfen https://github.com/aria2/aria2/releases adresinden indirin" -ForegroundColor Yellow
        Write-Host "  ve aria2c.exe dosyasini PATH'e ekleyin." -ForegroundColor Yellow
        exit 1
    }
}
Write-Host "  [*] aria2c kontrolu OK" -ForegroundColor Green

# pip bagimliliklari
Write-Host "  [*] Python paketleri yukleniyor..."
python -m pip install -r requirements.txt --quiet
Write-Host "  [*] Python paketleri OK" -ForegroundColor Green

# Playwright browser
Write-Host "  [*] Playwright Chromium yukleniyor..."
python -m playwright install chromium
Write-Host "  [*] Playwright OK" -ForegroundColor Green

Write-Host ""
Write-Host "  [OK] Kurulum tamamlandi!" -ForegroundColor Green
Write-Host "  Kullanim: python run.py <url>" -ForegroundColor White
Write-Host ""
