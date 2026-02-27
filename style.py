import questionary


# ── ANSI Theme ──────────────────────────────────────────
class C:
    RST   = "\033[0m"
    BOLD  = "\033[1m"
    DIM   = "\033[2m"
    # foreground
    RED   = "\033[31m"
    GREEN = "\033[32m"
    YELLOW= "\033[33m"
    BLUE  = "\033[34m"
    CYAN  = "\033[36m"
    WHITE = "\033[97m"
    GRAY  = "\033[90m"

def banner():
    print(f"""
{C.CYAN}{C.BOLD}  ╔══════════════════════════════════════════════╗
  ║        A N I M E  D O W N L O A D E R        ║
  ╚═════════════════════════════════════════════╝{C.RST}
""")

def info(msg):    print(f"  {C.CYAN}[*]{C.RST} {msg}")
def success(msg): print(f"  {C.GREEN}[✓]{C.RST} {msg}")
def warn(msg):    print(f"  {C.YELLOW}[!]{C.RST} {msg}")
def error(msg):   print(f"  {C.RED}[✗]{C.RST} {msg}")
def step(n, total, msg): print(f"\n  {C.BLUE}{C.BOLD}[{n}/{total}]{C.RST} {C.WHITE}{msg}{C.RST}")
def dim(msg):     print(f"  {C.GRAY}{msg}{C.RST}")
def bar(char="─", width=50): print(f"  {C.GRAY}{char*width}{C.RST}")

Q_STYLE = questionary.Style([
    ("qmark",       "fg:cyan bold"),
    ("question",    "fg:white bold"),
    ("pointer",     "fg:cyan bold"),
    ("highlighted", "fg:cyan bold"),
    ("selected",    "fg:green"),
    ("answer",      "fg:green bold"),
    ("instruction", "fg:ansigray italic"),
    ("separator",   "fg:ansigray"),
])
