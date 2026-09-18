"""Painel do operador no navegador, publicado em `app.<dominio>`.

Uma decisão importante de fronteira: **`/admin` continua sem sair da VPS**. O painel não é um
cliente do `/admin` com a chave no navegador; ele é um caminho próprio, autenticado por sessão, que
chama os mesmos `servico.py` e `repo.py` que as rotas administrativas chamam. Assim a regra "nunca
publique /admin no Caddy" segue valendo, e nenhuma regra de negócio existe duas vezes.

O Caddy publica este host só quando o operador escolhe o painel na instalação. Sem isso, a API
continua exatamente como sempre foi, e `painel_ativo` nasce desligado.
"""

import uuid
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.agentes import repo as agentes_repo
from app.clientes import repo as clientes_repo
from app.consumo import servico as consumo_servico
from app.painel import repo, servico
from app.plataforma.banco import sessao
from app.plataforma.config import config

AQUI = Path(__file__).parent
ESTATICOS = AQUI / "estaticos"

router = APIRouter(prefix="/painel")
paginas = Jinja2Templates(directory=str(AQUI / "paginas"))

LIMITE_RESUMO_DA_FALHA = 90


def resumo_da_falha(detalhe: dict[str, Any] | None) -> str:
    """O `detalhe` da falha é JSON livre, com o que o provedor ou o canal devolveram.

    Nunca vai inteiro para a tela: já apareceu ali resposta crua de API com pedaço de chave. Sai o
    mesmo pedaço curto que o menu do terminal mostra, para as duas telas dizerem a mesma coisa.
    """
    bruto = (detalhe or {}).get("erro") or (detalhe or {}).get("problemas") or ""
    return " ".join(str(bruto).split())[:LIMITE_RESUMO_DA_FALHA]


def hora_curta(quando: Any) -> str:
    return quando.strftime("%d/%m %H:%M") if hasattr(quando, "strftime") else ""


paginas.env.filters["resumo_da_falha"] = resumo_da_falha
paginas.env.filters["hora_curta"] = hora_curta

COOKIE = "asimov_painel"
CANAIS = {
    "chatwoot": "Chatwoot",
    "whatsapp": "WhatsApp oficial",
    "waha": "WhatsApp (WAHA)",
    "nativo": "Nativo",
}


def _cookie(resposta: RedirectResponse, token: str) -> RedirectResponse:
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


def _de_onde(request: Request) -> str:
    return request.client.host if request.client else "desconhecido"


def _hospedeiro(endereco: str) -> str:
    """Host e porta em minúsculas, sem a porta padrão do esquema."""
    partes = urlsplit(endereco if "//" in endereco else "//" + endereco)
    hospedeiro = (partes.hostname or "").lower()
    porta = partes.port
    if porta and porta not in (80, 443):
        return f"{hospedeiro}:{porta}"
    return hospedeiro


def _mesma_origem(request: Request) -> bool:
    """Defesa de CSRF. O cookie já é `SameSite=Strict`; a origem confere o resto.

    A comparação é por host, nunca por prefixo de texto: `painel.exemplo.com.br.outracoisa.com`
    começa com o endereço certo e não é ele. Pedido sem `Origin` nem `Referer` passa, que é o que
    um formulário do próprio painel manda em navegador antigo, e aí o cookie estrito é quem segura.
    """
    bruto = request.headers.get("origin") or request.headers.get("referer") or ""
    if not bruto:
        return True
    de_onde = _hospedeiro(bruto)
    if not de_onde:
        return False
    daqui = {_hospedeiro(str(request.base_url)), _hospedeiro(request.headers.get("host", ""))}
    if config().subdominio_app:
        daqui.add(_hospedeiro(config().subdominio_app))
    return de_onde in {h for h in daqui if h}


async def exige_sessao(request: Request) -> None:
    if not await servico.sessao_vale(request.cookies.get(COOKIE, "")):
        raise HTTPException(status_code=401, detail="entre no painel")


def _tela(request: Request, nome: str, **dados: Any) -> HTMLResponse:
    return paginas.TemplateResponse(request, nome, {"cfg": config(), "canais": CANAIS, **dados})


@router.get("/painel.css", include_in_schema=False)
async def folha_de_estilo() -> FileResponse:
    """Um arquivo, servido daqui mesmo. Nada de CDN: o painel é da VPS do operador."""
    return FileResponse(ESTATICOS / "painel.css", media_type="text/css")


@router.get("", include_in_schema=False)
@router.get("/", include_in_schema=False)
async def raiz(request: Request, s: AsyncSession = Depends(sessao)) -> RedirectResponse:
    """Uma porta só: manda para criar o acesso, entrar ou para o painel, conforme o estado."""
    if await repo.operador(s) is None:
        return RedirectResponse("/painel/primeiro-acesso", status_code=303)
    if not await servico.sessao_vale(request.cookies.get(COOKIE, "")):
        return RedirectResponse("/painel/entrar", status_code=303)
    return RedirectResponse("/painel/inicio", status_code=303)


# Entrar


@router.get("/entrar", response_class=HTMLResponse, include_in_schema=False)
async def tela_entrar(request: Request, s: AsyncSession = Depends(sessao)) -> Any:
    if await repo.operador(s) is None:
        return RedirectResponse("/painel/primeiro-acesso", status_code=303)
    return _tela(request, "entrar.html")


@router.post("/entrar", include_in_schema=False)
async def entrar(
    request: Request, senha: str = Form(default=""), s: AsyncSession = Depends(sessao)
) -> Any:
    if not _mesma_origem(request):
        raise HTTPException(status_code=403, detail="pedido de outra origem")
    de_onde = _de_onde(request)
    if await servico.em_espera(de_onde):
        return _tela(request, "entrar.html", erro="Tentativas demais. Espere 15 minutos.")

    usuario = await repo.operador(s)
    if usuario is None or not servico.confere_senha(senha, usuario.senha):
        restam = await servico.erro_de_senha(de_onde)
        return _tela(
            request,
            "entrar.html",
            erro=f"Senha incorreta. Restam {restam} tentativas antes da espera."
            if restam
            else "Tentativas demais. Espere 15 minutos.",
        )

    await servico.limpa_erros(de_onde)
    await repo.marca_acesso(s, usuario)
    await s.commit()
    return _cookie(RedirectResponse("/painel/inicio", status_code=303), await servico.abre_sessao())


@router.post("/sair", include_in_schema=False)
async def sair(request: Request) -> RedirectResponse:
    await servico.fecha_sessao(request.cookies.get(COOKIE, ""))
    resposta = RedirectResponse("/painel/entrar", status_code=303)
    resposta.delete_cookie(COOKIE, path="/painel")
    return resposta


# Primeiro acesso


@router.get("/primeiro-acesso", response_class=HTMLResponse, include_in_schema=False)
async def tela_primeiro_acesso(request: Request, s: AsyncSession = Depends(sessao)) -> Any:
    if await repo.operador(s) is not None:
        return RedirectResponse("/painel/entrar", status_code=303)
    return _tela(request, "primeiro_acesso.html")


@router.post("/primeiro-acesso", include_in_schema=False)
async def primeiro_acesso(
    request: Request,
    codigo: str = Form(default=""),
    senha: str = Form(default=""),
    senha2: str = Form(default=""),
    s: AsyncSession = Depends(sessao),
) -> Any:
    if not _mesma_origem(request):
        raise HTTPException(status_code=403, detail="pedido de outra origem")
    if await repo.operador(s) is not None:
        return RedirectResponse("/painel/entrar", status_code=303)

    de_onde = _de_onde(request)
    if await servico.em_espera(de_onde):
        return _tela(request, "primeiro_acesso.html", erro="Tentativas demais. Espere 15 minutos.")
    if senha != senha2:
        return _tela(request, "primeiro_acesso.html", erro="As duas senhas não são iguais.")
    if motivo := servico.senha_fraca(senha):
        return _tela(request, "primeiro_acesso.html", erro=motivo)
    if not await servico.codigo_vale(codigo):
        await servico.erro_de_senha(de_onde)
        return _tela(
            request,
            "primeiro_acesso.html",
            erro="Código inválido ou vencido. Rode asimov painel na VPS para gerar outro.",
        )

    try:
        await repo.cria(s, servico.cifra_senha(senha))
        await s.commit()
    except IntegrityError:
        # Dois cadastros ao mesmo tempo: o banco deixa passar um só, e o outro vai para o login.
        await s.rollback()
        return RedirectResponse("/painel/entrar", status_code=303)
    # O código só se gasta depois de a conta existir: criação que falha no meio não deixa o
    # operador sem código e sem conta.
    await servico.gasta_codigo(codigo)
    await servico.limpa_erros(de_onde)
    return _cookie(RedirectResponse("/painel/inicio", status_code=303), await servico.abre_sessao())


# Painel


@router.get(
    "/inicio", response_class=HTMLResponse, include_in_schema=False, dependencies=[Depends(exige_sessao)]
)
async def inicio(request: Request, s: AsyncSession = Depends(sessao)) -> HTMLResponse:
    agentes = await agentes_repo.listar_de_todos_os_clientes(s)
    clientes = {c.id: c.nome for c in await clientes_repo.listar(s)}
    consumo = await consumo_servico.relatorio(s, dias=7)
    return _tela(
        request,
        "inicio.html",
        agentes=agentes,
        clientes=clientes,
        consumo=consumo,
        custo=sum(a.get("custo", 0) or 0 for a in consumo["agentes"]),
        turnos=sum(a.get("turnos", 0) or 0 for a in consumo["agentes"]),
    )


@router.get(
    "/agentes", response_class=HTMLResponse, include_in_schema=False, dependencies=[Depends(exige_sessao)]
)
async def lista_agentes(
    request: Request, cliente_id: uuid.UUID | None = None, s: AsyncSession = Depends(sessao)
) -> HTMLResponse:
    agentes = (
        await agentes_repo.listar(s, cliente_id)
        if cliente_id
        else await agentes_repo.listar_de_todos_os_clientes(s)
    )
    clientes = await clientes_repo.listar(s)
    return _tela(
        request,
        "agentes.html",
        agentes=agentes,
        clientes=clientes,
        nomes={c.id: c.nome for c in clientes},
        escolhido=cliente_id,
    )
