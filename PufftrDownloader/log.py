from datetime import datetime
from .style import warn, error

WARN_LOG_FILE = None
DEBUGLEVEL = 0


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