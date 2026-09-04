import secrets
from urllib.parse import urlencode
from datetime import datetime, timezone, timedelta
import httpx
from config import settings
from database import SessionLocal, OAuthState, TikTokAccount
from database import get_user
from services.crypto import encrypt
from sqlalchemy import select, delete
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

TOKEN_URL = "https://open.tiktokapis.com/v2/oauth/token/"
AUTHORIZE_URL = "https://www.tiktok.com/v2/auth/authorize/"

class OAuthService:
    async def authorization_url(self, telegram_user_id: int):
        state = secrets.token_urlsafe(32)
        async with SessionLocal() as s:
            s.add(OAuthState(state=state, telegram_user_id=telegram_user_id))
            await s.commit()
        params = {
            "client_key": settings.tiktok_client_key,
            "response_type": "code",
            "scope": settings.tiktok_scopes,
            "redirect_uri": settings.tiktok_redirect_uri,
            "state": state,
        }
        return AUTHORIZE_URL + "?" + urlencode(params)

    async def handle_callback(self, code: str, state: str):
        async with SessionLocal() as s:
            row = (await s.execute(select(OAuthState).where(OAuthState.state == state))).scalar_one_or_none()
            if not row:
                return {"ok": False, "message": "OAuth state غير صالح أو انتهت صلاحيته."}
            tg_id = row.telegram_user_id
            await s.delete(row)
            await s.commit()

        data = {
            "client_key": settings.tiktok_client_key,
            "client_secret": settings.tiktok_client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": settings.tiktok_redirect_uri,
        }
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(TOKEN_URL, data=data)
        payload = r.json()
        if r.status_code >= 400 or payload.get("error"):
            return {"ok": False, "message": "TikTok رفض ربط الحساب. راجع إعدادات التطبيق والصلاحيات."}
        now = datetime.now(timezone.utc)
        async with SessionLocal() as s:
            existing = (await s.execute(select(TikTokAccount).where(TikTokAccount.user_id == (await get_user(tg_id, s)).id))).scalar_one_or_none()
            obj = existing or TikTokAccount(user_id=(await get_user(tg_id, s)).id, open_id=payload["open_id"],
                                            access_token_enc=encrypt(payload["access_token"]),
                                            refresh_token_enc=encrypt(payload["refresh_token"]),
                                            access_expires_at=now + timedelta(seconds=int(payload["expires_in"])),
                                            refresh_expires_at=now + timedelta(seconds=int(payload.get("refresh_expires_in", 0))) if payload.get("refresh_expires_in") else None,
                                            scopes=payload.get("scope", ""))
            if existing:
                obj.open_id = payload["open_id"]
                obj.access_token_enc = encrypt(payload["access_token"])
                obj.refresh_token_enc = encrypt(payload["refresh_token"])
                obj.access_expires_at = now + timedelta(seconds=int(payload["expires_in"]))
                obj.refresh_expires_at = now + timedelta(seconds=int(payload.get("refresh_expires_in", 0))) if payload.get("refresh_expires_in") else None
                obj.scopes = payload.get("scope", "")
                obj.updated_at = now
            s.add(obj)
            await s.commit()
        return {"ok": True, "message": "تم الربط."}
