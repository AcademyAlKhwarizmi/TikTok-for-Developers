from pathlib import Path
from config import settings

VIDEO_EXTS = {".mp4", ".mov", ".webm", ".m4v"}
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}

def validate_media(path: str, media_type: str):
    p = Path(path)
    if not p.exists():
        return False, "الملف مش موجود."
    if p.stat().st_size > settings.max_media_mb * 1024 * 1024:
        return False, f"الملف أكبر من {settings.max_media_mb}MB."
    ext = p.suffix.lower()
    allowed = VIDEO_EXTS if media_type == "video" else IMAGE_EXTS
    if ext not in allowed:
        return False, "الصيغة دي مش مدعومة."
    return True, ""

def normalize_hashtags(value: str) -> str:
    tags = []
    for raw in value.replace(",", " ").split():
        if not raw.startswith("#"):
            raw = "#" + raw
        tags.append(raw)
    return " ".join(tags)
