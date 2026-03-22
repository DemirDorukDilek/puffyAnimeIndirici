#!/usr/bin/env bash
set -e

echo ""
echo "  ╔══════════════════════════════════════════════╗"
echo "  ║        A N I M E  D O W N L O A D E R        ║"
echo "  ║               K U R U L U M                   ║"
echo "  ╚══════════════════════════════════════════════╝"
echo ""

# Python kontrolu
if ! command -v python3 &>/dev/null; then
    echo "  [X] python3 bulunamadi. Lutfen Python 3.10+ kurun."
    exit 1
fi

PYVER=$(python3 -c "import sys; print(sys.version_info.minor)")
if [ "$PYVER" -lt 10 ]; then
    echo "  [!] Python 3.10 veya uzeri gerekli. Mevcut surum: 3.$PYVER"
    exit 1
fi

echo "  [*] Python kontrolu OK"

# aria2c kontrolu
if ! command -v aria2c &>/dev/null; then
    echo "  [*] aria2c bulunamadi, yukleniyor..."
    if command -v apt &>/dev/null; then
        sudo apt install -y aria2
    elif command -v pacman &>/dev/null; then
        sudo pacman -S --noconfirm aria2
    elif command -v dnf &>/dev/null; then
        sudo dnf install -y aria2
    elif command -v brew &>/dev/null; then
        brew install aria2
    else
        echo "  [X] aria2c otomatik yuklenemedi. Paket yoneticinizle kurun: aria2"
        exit 1
    fi
fi
echo "  [*] aria2c kontrolu OK"

# pip bagimliliklari
echo "  [*] Python paketleri yukleniyor..."
pip install -r requirements.txt --quiet
echo "  [*] Python paketleri OK"

# Playwright browser
echo "  [*] Playwright Chromium yukleniyor..."
python3 -m playwright install chromium
echo "  [*] Playwright OK"

echo ""
echo "  [OK] Kurulum tamamlandi!"
echo "  Kullanim: python3 run.py <url>"
echo ""
