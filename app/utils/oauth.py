"""
OAuth configuration using Authlib
"""
import os
from authlib.integrations.starlette_client import OAuth
from starlette.config import Config

# Load environment variables
config = Config(environ=os.environ)

# Initialize OAuth registry
oauth = OAuth()

# Google OAuth2 (OIDC)
oauth.register(
    name='google',
    client_id=os.getenv('GOOGLE_CLIENT_ID'),
    client_secret=os.getenv('GOOGLE_CLIENT_SECRET'),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={
        'scope': 'openid email profile'
    }
)

# Naver OAuth2
oauth.register(
    name='naver',
    client_id=os.getenv('NAVER_CLIENT_ID'),
    client_secret=os.getenv('NAVER_CLIENT_SECRET'),
    authorize_url='https://nid.naver.com/oauth2.0/authorize',
    authorize_params=None,
    access_token_url='https://nid.naver.com/oauth2.0/token',
    access_token_params=None,
    refresh_token_url=None,
    client_kwargs={
        'scope': 'profile'
    }
)


def get_oauth_client(provider: str):
    """
    Get OAuth client by provider name

    Args:
        provider: OAuth provider name ('google' or 'naver')

    Returns:
        OAuth client instance

    Raises:
        ValueError: If provider is not supported
    """
    if provider not in ['google', 'naver']:
        raise ValueError(f"Unsupported OAuth provider: {provider}")

    return getattr(oauth, provider)
