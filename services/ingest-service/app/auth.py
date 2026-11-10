from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException

from .cognito import verify_access_token
from .config import Settings, get_settings


@dataclass(frozen=True)
class Principal:
    sub: str
    name: str
    email: str


def get_principal(authorization: str | None = Header(default=None), settings: Settings = Depends(get_settings)) -> Principal:
    if settings.mock_auth:
        if settings.app_env.lower() != "local":
            raise HTTPException(status_code=503, detail="Mock authentication is only available in local mode")
        return Principal(sub="demo-user-001", name="Alex Morgan", email="alex@echoscript.local")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authentication required")
    claims = verify_access_token(authorization.removeprefix("Bearer ").strip(), settings.cognito_issuer, settings.cognito_client_id)
    return Principal(sub=claims["sub"], name=claims.get("name", "EchoScript user"), email=claims.get("email", ""))
