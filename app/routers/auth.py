"""
OAuth authentication routes (Google, Naver)
"""
import os
from typing import Optional
from fastapi import APIRouter, Request, HTTPException, Depends, Response
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from app.db import get_db
from app.models.db import User
from app.utils.oauth import oauth
from app.utils.jwt import create_access_token
import httpx

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

# Configuration
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8080")
IS_PRODUCTION = os.getenv("ENV", "development") == "production"


@router.get("/login/{provider}")
async def login(provider: str, request: Request):
    """
    Initiate OAuth login flow

    Args:
        provider: OAuth provider ('google' or 'naver')

    Returns:
        Redirect to OAuth provider's authorization page
    """
    if provider not in ['google', 'naver']:
        raise HTTPException(status_code=400, detail="Unsupported provider")

    # OAuth client
    client = getattr(oauth, provider)

    # Redirect URI for callback - use explicit BACKEND_URL to avoid proxy/domain issues
    redirect_uri = f"{BACKEND_URL}/api/auth/callback/{provider}"

    # Redirect to OAuth provider
    return await client.authorize_redirect(request, redirect_uri)


@router.get("/callback/{provider}", name="auth_callback")
async def auth_callback(
    provider: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    OAuth callback endpoint - handles user authentication and JWT creation

    Flow:
        1. Exchange authorization code for access token
        2. Fetch user info from provider
        3. Upsert user in database
        4. Generate JWT token
        5. Set HttpOnly cookie
        6. Redirect to frontend

    Args:
        provider: OAuth provider ('google' or 'naver')
        request: FastAPI request
        db: Database session

    Returns:
        Redirect to frontend with JWT in HttpOnly cookie
    """
    if provider not in ['google', 'naver']:
        raise HTTPException(status_code=400, detail="Unsupported provider")

    try:
        # OAuth client
        client = getattr(oauth, provider)

        # Exchange code for token
        token = await client.authorize_access_token(request)

        # Get user info based on provider
        if provider == 'google':
            # Google uses OIDC - userinfo is in token
            user_info = token.get('userinfo')
            if not user_info:
                raise HTTPException(status_code=400, detail="Failed to get user info")

            email = user_info.get('email')
            name = user_info.get('name')
            provider_id = user_info.get('sub')

        elif provider == 'naver':
            # Naver requires separate API call
            access_token = token.get('access_token')
            if not access_token:
                raise HTTPException(status_code=400, detail="Failed to get access token")

            # Fetch user profile from Naver API
            async with httpx.AsyncClient() as http_client:
                headers = {'Authorization': f'Bearer {access_token}'}
                response = await http_client.get(
                    'https://openapi.naver.com/v1/nid/me',
                    headers=headers
                )
                response.raise_for_status()
                data = response.json()

                if data.get('resultcode') != '00':
                    raise HTTPException(status_code=400, detail="Failed to get user info from Naver")

                user_info = data.get('response', {})
                email = user_info.get('email')
                name = user_info.get('name')
                provider_id = user_info.get('id')

        if not email or not provider_id:
            raise HTTPException(status_code=400, detail="Email or provider ID missing")

        # Upsert user in database
        user = db.query(User).filter(
            User.provider == provider,
            User.provider_id == provider_id
        ).first()

        if user:
            # Update existing user
            user.email = email
            user.name = name
        else:
            # Create new user
            user = User(
                email=email,
                name=name,
                provider=provider,
                provider_id=provider_id
            )
            db.add(user)

        db.commit()
        db.refresh(user)

        # Generate JWT token
        access_token = create_access_token(data={"sub": user.id})

        # Create redirect response
        redirect_url = f"{FRONTEND_URL}"
        response = RedirectResponse(url=redirect_url)

        # Set HttpOnly cookie with SameSite=None for cross-site requests
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            secure=True,  # Required for SameSite=None
            samesite="none",  # Allow cross-site cookie (frontend → API)
            path="/",
            max_age=7 * 24 * 60 * 60  # 7 days
        )

        return response

    except Exception as e:
        # Redirect to frontend error page
        error_url = f"{FRONTEND_URL}/auth/error?message={str(e)}"
        return RedirectResponse(url=error_url)


@router.post("/logout")
async def logout():
    """
    Logout user by clearing the access token cookie

    Returns:
        Response with cleared cookie

    Note:
        Manually sets Set-Cookie header to ensure SameSite=None is properly applied.
        FastAPI's set_cookie() may not correctly handle samesite="none" in some cases.
        This is required for proper cookie deletion in CORS + credentials scenarios.
    """
    response = JSONResponse(content={"message": "Logged out successfully"})

    # Manually build Set-Cookie header to ensure SameSite=None
    # Must match login cookie attributes exactly: httponly, secure, samesite, path
    cookie_header = (
        "access_token=; "
        "Path=/; "
        "HttpOnly; "
        "Secure; "
        "SameSite=None; "
        "Max-Age=0"
    )
    response.headers["Set-Cookie"] = cookie_header

    return response
