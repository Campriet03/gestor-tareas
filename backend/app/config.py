import os
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[2]


def load_env(path=ROOT / ".env"):
    """Lee el .env de la raiz sin pisar variables ya definidas."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


def database_url():
    if os.getenv("DATABASE_URL"):
        return os.environ["DATABASE_URL"]
    user = quote(os.getenv("DB_USER", ""), safe="")
    password = quote(os.getenv("DB_PASSWORD", ""), safe="")
    host = os.getenv("DB_HOST", "127.0.0.1")
    port = os.getenv("DB_PORT", "3306")
    return f"mysql://{user}:{password}@{host}:{port}/{os.getenv('DB_NAME', '')}"


def parse_duration(text):
    """'1h', '30m', '45s', '2d' -> segundos."""
    units = {"s": 1, "m": 60, "h": 3600, "d": 86400}
    text = str(text).strip()
    if text and text[-1] in units:
        return int(text[:-1]) * units[text[-1]]
    return int(text)
