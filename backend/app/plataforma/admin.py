import hmac

from fastapi import Header, HTTPException

from app.plataforma.config import config


async def exige_admin(x_admin_key: str = Header(default="")) -> None:
    """Rotas /admin só respondem com a chave gerada pelo setup. O Caddy nem as publica."""
    if not x_admin_key or not hmac.compare_digest(x_admin_key, config().chave_api_admin):
        raise HTTPException(status_code=401, detail="chave administrativa inválida")
