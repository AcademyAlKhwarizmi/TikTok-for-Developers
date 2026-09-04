import math
import httpx
from pathlib import Path
from services.token_manager import TokenManager

BASE = "https://open.tiktokapis.com"

class TikTokAPI:
    def __init__(self):
        self.tokens = TokenManager()

    async def creator_info(self, user_id: int):
        token = await self.tokens.get_access_token(user_id)
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(f"{BASE}/v2/post/publish/creator_info/query/",
                                  headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
        data = r.json()
        if r.status_code >= 400 or data.get("error", {}).get("code") != "ok":
            raise RuntimeError(data.get("error", {}).get("message", "TikTok creator info failed"))
        return data["data"]

    async def direct_video(self, user_id: int, path: str, caption: str):
        token = await self.tokens.get_access_token(user_id)
        size = Path(path).stat().st_size
        chunk = min(max(size, 5 * 1024 * 1024), 64 * 1024 * 1024)
        # TikTok permits a whole-file upload for files <= 64 MB; for larger files we use chunks.
        if size < 5 * 1024 * 1024:
            chunk = size
        total = math.ceil(size / chunk)
        info = await self.creator_info(user_id)
        privacy = "PUBLIC_TO_EVERYONE" if "PUBLIC_TO_EVERYONE" in info.get("privacy_level_options", []) else info["privacy_level_options"][0]
        payload = {
            "post_info": {"title": caption[:2200], "privacy_level": privacy},
            "source_info": {"source": "FILE_UPLOAD", "video_size": size,
                            "chunk_size": chunk, "total_chunk_count": total}
        }
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(f"{BASE}/v2/post/publish/video/init/",
                                  headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                                  json=payload)
        body = r.json()
        if r.status_code >= 400 or body.get("error", {}).get("code") != "ok":
            raise RuntimeError(body.get("error", {}).get("message", "TikTok video init failed"))
        upload_url, publish_id = body["data"]["upload_url"], body["data"]["publish_id"]
        with open(path, "rb") as f:
            async with httpx.AsyncClient(timeout=180) as client:
                for index in range(total):
                    start = index * chunk
                    end = min(start + chunk, size)
                    f.seek(start)
                    binary = f.read(end - start)
                    headers = {
                        "Content-Type": "video/mp4",
                        "Content-Range": f"bytes {start}-{end-1}/{size}",
                    }
                    rr = await client.put(upload_url, headers=headers, content=binary)
                    if rr.status_code not in (201, 206):
                        raise RuntimeError(f"TikTok upload failed: HTTP {rr.status_code}")
        return publish_id

    async def direct_photo(self, user_id: int, public_url: str, caption: str):
        token = await self.tokens.get_access_token(user_id)
        info = await self.creator_info(user_id)
        privacy = "PUBLIC_TO_EVERYONE" if "PUBLIC_TO_EVERYONE" in info.get("privacy_level_options", []) else info["privacy_level_options"][0]
        payload = {
            "post_mode": "DIRECT_POST",
            "media_type": "PHOTO",
            "post_info": {"description": caption[:4000], "privacy_level": privacy},
            "source_info": {"source": "PULL_FROM_URL", "photo_images": [public_url], "photo_cover_index": 0}
        }
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(f"{BASE}/v2/post/publish/content/init/",
                                  headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                                  json=payload)
        body = r.json()
        if r.status_code >= 400 or body.get("error", {}).get("code") != "ok":
            raise RuntimeError(body.get("error", {}).get("message", "TikTok photo init failed"))
        return body["data"]["publish_id"]

    async def status(self, user_id: int, publish_id: str):
        token = await self.tokens.get_access_token(user_id)
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(f"{BASE}/v2/post/publish/status/fetch/",
                                  headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                                  json={"publish_id": publish_id})
        body = r.json()
        if r.status_code >= 400 or body.get("error", {}).get("code") != "ok":
            raise RuntimeError(body.get("error", {}).get("message", "TikTok status failed"))
        return body["data"]
