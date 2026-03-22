from PufftrDownloader import run,DEBUGLEVEL
import sys,os

if DEBUGLEVEL > 0:
    url = "https://puffytr.com/takopii-no-genzai-5-bolum-izle"
else:
    if len(sys.argv) == 1:
        url = input("url: ")
        # url = "https://anizm.net/yuusha-kei-ni-shosu-choubatsu-yuusha-9004-tai-keimu-kiroku-1-bolum-izle"
    else:
        if sys.argv[1] == "-conf":
            os.system("nano conf.json")
            exit(0)
        url = sys.argv[1]
run(url)