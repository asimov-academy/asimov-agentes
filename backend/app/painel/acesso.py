"""Sessão, origem e CSRF do painel, num lugar só.

As páginas Jinja2 (`rotas.py`) e o front em React (`api.py`) passam pelas mesmas conferências. Sem
isto, cada superfície teria a sua cópia da regra, que é exatamente como se esquece uma delas.
"""

from urllib.parse import urlsplit

from fastapi import HTTPException, Request
from fastapi.responses import Response

from app.painel import servico
from app.plataforma.config import config

COOKIE = "asimov_painel"
CABECALHO_CSRF = "X-Painel-CSRF"


def poe_cookie(resposta: Response, token: str) -> Response:
    resposta.set_cookie(
        COOKIE,
        token,
        max_age=servico.DURACAO_SESSAO_SEGUNDOS,
        httponly=True,
        secure=True,
        samesite="strict",
        path="/painel",
    )
    return resposta


def token_da_sessao(request: Request) -> str:
    return request.cookies.get(COOKIE, "")


def quem_chama(request: Request) -> str:
    return request.client.host if request.client else "desconhecido"


def hospedeiro(endereco: str) -> str:
    """Host e porta em minúsculas, sem a porta padrão do esquema."""
    partes = urlsplit(endereco if "//" in endereco else "//" + endereco)
    nome = (partes.hostname or "").lower()
    porta = partes.port
    if porta and porta not in (80, 443):
        return f"{nome}:{porta}"
    return nome


def mesma_origem(request: Request) -> bool:
    """Defesa de CSRF. O cookie já é `SameSite=Strict`; a origem confere o resto.

    A comparação é por host, nunca por prefixo de texto: `painel.exemplo.com.br.outracoisa.com`
    começa com o endereço certo e não é ele. Pedido sem `Origin` nem `Referer` passa, que é o que
    um formulário do próprio painel manda em navegador antigo, e aí o cookie estrito é quem segura.
    """
    bruto = request.headers.get("origin") or request.headers.get("referer") or ""
    if not bruto:
        return True
    veio_de = hospedeiro(bruto)
    if not veio_de:
        return False
    daqui = {hospedeiro(str(request.base_url)), hospedeiro(request.headers.get("host", ""))}
    if config().subdominio_app:
        daqui.add(hospedeiro(config().subdominio_app))
    return veio_de in {h for h in daqui if h}


async def exige_sessao(request: Request) -> None:
    if not await servico.sessao_vale(token_da_sessao(request)):
        raise HTTPException(status_code=401, detail="entre no painel")


async def exige_csrf(request: Request) -> None:
    """Vale para toda escrita do front. Leitura passa direto: ela não muda nada.

    O cabeçalho só existe para quem leu `GET /painel/api/eu`, e ler a resposta exige a sessão. Um
    site de terceiro consegue disparar o pedido com o cookie junto, mas não consegue ler nada para
    montar o cabeçalho.
    """
    if request.method == "GET":
        return
    if not mesma_origem(request):
        raise HTTPException(status_code=403, detail="pedido de outra origem")
    if not servico.csrf_confere(token_da_sessao(request), request.headers.get(CABECALHO_CSRF, "")):
        raise HTTPException(status_code=403, detail="token de escrita ausente ou inválido")
