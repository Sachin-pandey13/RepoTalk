"""
backend/routes/auth.py
GitHub & Google OAuth flows + session management.
"""
import secrets
import httpx
from fastapi import APIRouter, Depends, HTTPException, Response, Request, status
from fastapi.responses import RedirectResponse

from backend.core.config import settings
from backend.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_current_user_id,
    CREDENTIALS_EXCEPTION,
)
from backend.services.user_service import upsert_user, get_user_by_id

router = APIRouter(prefix="/auth", tags=["auth"])

# ── Helpers ──────────────────────────────────────────────────────────────────

COOKIE_OPTS = dict(
    httponly=True,
    samesite="lax",
    secure=False,        # Set True in production (HTTPS)
)


def _set_auth_cookies(response: Response, user_id: int) -> None:
    access = create_access_token({"sub": str(user_id)})
    refresh = create_refresh_token({"sub": str(user_id)})
    response.set_cookie(
        "access_token",
        access,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        **COOKIE_OPTS,
    )
    response.set_cookie(
        "refresh_token",
        refresh,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        **COOKIE_OPTS,
    )


# ── GitHub ───────────────────────────────────────────────────────────────────

@router.get("/github")
def github_login():
    """Redirect the browser to GitHub's OAuth authorise URL."""
    if not settings.GITHUB_CLIENT_ID:
        raise HTTPException(503, "GitHub OAuth not configured")
    state = secrets.token_urlsafe(16)
    url = (
        "https://github.com/login/oauth/authorize"
        f"?client_id={settings.GITHUB_CLIENT_ID}"
        f"&redirect_uri={settings.GITHUB_REDIRECT_URI}"
        f"&scope=user:email"
        f"&state={state}"
    )
    return RedirectResponse(url)


@router.get("/github/callback")
async def github_callback(code: str, state: str, response: Response):
    """Exchange the GitHub code for user info and issue session cookies."""
    if not settings.GITHUB_CLIENT_ID:
        raise HTTPException(503, "GitHub OAuth not configured")

    async with httpx.AsyncClient() as client:
        # 1. Exchange code for access token
        token_resp = await client.post(
            "https://github.com/login/oauth/access_token",
            json={
                "client_id": settings.GITHUB_CLIENT_ID,
                "client_secret": settings.GITHUB_CLIENT_SECRET,
                "code": code,
                "redirect_uri": settings.GITHUB_REDIRECT_URI,
            },
            headers={"Accept": "application/json"},
            timeout=15,
        )
        token_data = token_resp.json()
        gh_token = token_data.get("access_token")
        if not gh_token:
            raise HTTPException(400, "GitHub token exchange failed")

        # 2. Fetch user profile
        user_resp = await client.get(
            "https://api.github.com/user",
            headers={"Authorization": f"Bearer {gh_token}"},
            timeout=15,
        )
        gh_user = user_resp.json()

        # 3. Fetch primary email if not public
        email = gh_user.get("email")
        if not email:
            email_resp = await client.get(
                "https://api.github.com/user/emails",
                headers={"Authorization": f"Bearer {gh_token}"},
                timeout=15,
            )
            for entry in email_resp.json():
                if entry.get("primary"):
                    email = entry.get("email")
                    break

    user = upsert_user(
        provider="github",
        provider_id=str(gh_user["id"]),
        email=email,
        name=gh_user.get("name") or gh_user.get("login"),
        avatar_url=gh_user.get("avatar_url"),
        username=gh_user.get("login"),
    )

    redirect = RedirectResponse(
        url=f"{settings.FRONTEND_URL}/chat",
        status_code=status.HTTP_302_FOUND,
    )
    _set_auth_cookies(redirect, user["id"])
    return redirect


# ── Google ───────────────────────────────────────────────────────────────────

@router.get("/google")
def google_login():
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(503, "Google OAuth not configured")
    state = secrets.token_urlsafe(16)
    url = (
        "https://accounts.google.com/o/oauth2/v2/auth"
        f"?client_id={settings.GOOGLE_CLIENT_ID}"
        f"&redirect_uri={settings.GOOGLE_REDIRECT_URI}"
        f"&response_type=code"
        f"&scope=openid%20email%20profile"
        f"&state={state}"
        f"&access_type=offline"
    )
    return RedirectResponse(url)


@router.get("/google/callback")
async def google_callback(code: str, state: str, response: Response):
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(503, "Google OAuth not configured")

    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "code": code,
                "redirect_uri": settings.GOOGLE_REDIRECT_URI,
                "grant_type": "authorization_code",
            },
            timeout=15,
        )
        token_data = token_resp.json()
        id_token = token_data.get("id_token")
        if not id_token:
            raise HTTPException(400, "Google token exchange failed")

        # Decode ID token (without full verify for now; prod should use google-auth)
        import base64, json as _json
        parts = id_token.split(".")
        payload_bytes = parts[1] + "=" * (-len(parts[1]) % 4)
        claims = _json.loads(base64.urlsafe_b64decode(payload_bytes))

    user = upsert_user(
        provider="google",
        provider_id=claims["sub"],
        email=claims.get("email"),
        name=claims.get("name"),
        avatar_url=claims.get("picture"),
        username=claims.get("email", "").split("@")[0],
    )

    redirect = RedirectResponse(
        url=f"{settings.FRONTEND_URL}/chat",
        status_code=status.HTTP_302_FOUND,
    )
    _set_auth_cookies(redirect, user["id"])
    return redirect


# ── Session management ───────────────────────────────────────────────────────

@router.get("/me")
def me(user_id: int = Depends(get_current_user_id)):
    user = get_user_by_id(user_id)
    if not user:
        raise CREDENTIALS_EXCEPTION
    # Never leak DB internals
    return {
        "id": user["id"],
        "name": user["name"],
        "email": user["email"],
        "avatar_url": user["avatar_url"],
        "username": user["username"],
        "provider": user["provider"],
    }


@router.post("/refresh")
def refresh_token(
    response: Response,
    refresh_token: str | None = None,
):
    from fastapi import Cookie
    # Token comes from cookie
    if not refresh_token:
        raise CREDENTIALS_EXCEPTION
    payload = decode_token(refresh_token)
    if payload.get("type") != "refresh":
        raise CREDENTIALS_EXCEPTION
    user_id = int(payload["sub"])
    _set_auth_cookies(response, user_id)
    return {"message": "Token refreshed"}


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    return {"message": "Logged out"}
