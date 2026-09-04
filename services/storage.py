from pathlib import Path
from config import settings

class StorageService:
    @staticmethod
    def save_bytes(data: bytes, filename: str) -> str:
        folder = Path(settings.media_dir)
        folder.mkdir(parents=True, exist_ok=True)
        safe = Path(filename).name
        import secrets
        safe = secrets.token_hex(8) + "_" + safe
        path = folder / safe
        path.write_bytes(data)
        return str(path)

    @staticmethod
    def public_url(path: str):
        if not settings.public_base_url:
            return None
        return f"{settings.public_base_url}/media/{Path(path).name}"

    @staticmethod
    def resolve_filename(filename: str):
        # Prevent path traversal.
        safe = Path(filename).name
        path = Path(settings.media_dir) / safe
        return str(path) if path.exists() else None
