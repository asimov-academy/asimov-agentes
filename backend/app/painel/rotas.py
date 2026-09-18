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

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.agentes import repo as agentes_repo
from app.clientes import repo as clientes_repo
from app.consumo import servico as consumo_servico
from app.painel import repo, servico
from app.painel.acesso import COOKIE, exige_sessao, mesma_origem, poe_cookie, quem_chama
from app.painel.api import router as api
from app.painel.api_agentes import router as api_agentes
from app.painel.api_conversas import router as api_conversas
from app.plataforma.banco import sessao
from app.plataforma.config import config

AQUI = Path(__file__).parent
ESTATICOS = AQUI / "estaticos"

router = APIRouter(prefix="/painel")

# Onde o operador cai depois de entrar: o front em React, construído de `frontend/`.
PAINEL = "/painel/app"
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

CANAIS = {
    "chatwoot": "Chatwoot",
    "whatsapp": "WhatsApp oficial",
    "waha": "WhatsApp (WAHA)",
    "nativo": "Nativo",
}


def versao_da_folha() -> int:
    """A hora em que o `painel.css` mudou, para o endereço dele mudar junto.

    Sem isso o nome do arquivo é sempre o mesmo, o navegador guarda a folha e o operador continua
    vendo o estilo da versão passada depois de um `asimov atualizar`. Com a versão no endereço, o
    navegador pode guardar à vontade e ainda assim pegar a nova na hora.
    """
    try:
        return int((ESTATICOS / "painel.css").stat().st_mtime)
    except OSError:
        return 0


def _tela(request: Request, nome: str, **dados: Any) -> HTMLResponse:
    return paginas.TemplateResponse(
        request,
        nome,
        {"cfg": config(), "canais": CANAIS, "css_versao": versao_da_folha(), **dados},
    )


@router.get("/painel.css", include_in_schema=False)
async def folha_de_estilo() -> FileResponse:
    """Um arquivo, servido daqui mesmo. Nada de CDN: o painel é da VPS do operador.

    Sem cache: o nome do arquivo não muda entre versões, então o navegador guardava a folha antiga e
    o operador via o estilo da versão passada depois de um `asimov atualizar`. As fontes, essas sim,
    têm nome estável de verdade e podem ficar guardadas para sempre.
    """
    return FileResponse(
        ESTATICOS / "painel.css",
        media_type="text/css",
        # O endereço carrega a versão (`?v=`), então guardar à vontade é seguro: folha nova vem com
        # endereço novo.
        headers={"Cache-Control": "public, max-age=31536000"},
    )


FONTES = {
    "inter-latin-400-normal.woff2",
    "inter-latin-600-normal.woff2",
    "jetbrains-mono-latin-400-normal.woff2",
}


@router.get("/fontes/{arquivo}", include_in_schema=False)
async def fonte(arquivo: str) -> FileResponse:
    """As duas fontes do design system, servidas da VPS como todo o resto. Nada de CDN.

    A lista é fechada: nome fora dela não vira leitura de arquivo, mesmo com `..` no meio.
    """
    if arquivo not in FONTES:
        raise HTTPException(status_code=404, detail="fonte não encontrada")
    return FileResponse(
        ESTATICOS / "fontes" / arquivo,
        media_type="font/woff2",
        headers={"Cache-Control": "public, max-age=31536000, immutable"},
    )


@router.get("", include_in_schema=False)
@router.get("/", include_in_schema=False)
async def raiz(request: Request, s: AsyncSession = Depends(sessao)) -> RedirectResponse:
    """Uma porta só: manda para criar o acesso, entrar ou para o painel, conforme o estado."""
    if await repo.operador(s) is None:
        return RedirectResponse("/painel/primeiro-acesso", status_code=303)
    if not await servico.sessao_vale(request.cookies.get(COOKIE, "")):
        return RedirectResponse("/painel/entrar", status_code=303)
    return RedirectResponse(PAINEL, status_code=303)


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
    if not mesma_origem(request):
        raise HTTPException(status_code=403, detail="pedido de outra origem")
    de_onde = quem_chama(request)
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
    return poe_cookie(RedirectResponse(PAINEL, status_code=303), await servico.abre_sessao())


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
    if not mesma_origem(request):
        raise HTTPException(status_code=403, detail="pedido de outra origem")
    if await repo.operador(s) is not None:
        return RedirectResponse("/painel/entrar", status_code=303)

    de_onde = quem_chama(request)
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
    return poe_cookie(RedirectResponse(PAINEL, status_code=303), await servico.abre_sessao())


# As duas telas que o painel em React substituiu
#
# `inicio` e `agentes` eram as telas do painel em Jinja2, de antes de o front existir. Agora o
# mesmo dado está em `/painel/app`, com muito mais coisa, e manter as duas versões significaria
# manter dois painéis. Elas viram desvio, para endereço guardado nos favoritos não virar 404.


@router.get("/inicio", include_in_schema=False, dependencies=[Depends(exige_sessao)])
@router.get("/agentes", include_in_schema=False, dependencies=[Depends(exige_sessao)])
async def telas_antigas() -> RedirectResponse:
    return RedirectResponse(PAINEL, status_code=303)


# Front


def _pasta_do_front() -> Path:
    caminho = Path(config().diretorio_painel_app)
    return caminho if caminho.is_absolute() else AQUI.parent / caminho


SEM_BUILD = (
    "<!doctype html><meta charset=utf-8><title>Painel</title>"
    "<body style='background:#000;color:#e5e5e5;font-family:monospace;padding:3rem'>"
    "<h1>Front não construído</h1>"
    "<p>Rode <code>npm ci &amp;&amp; npm run build</code> em <code>frontend/</code>, ou suba a imagem "
    "de novo: o Dockerfile constrói sozinho.</p>"
)


@router.get("/app", include_in_schema=False)
@router.get("/app/{caminho:path}", include_in_schema=False)
async def front(request: Request, caminho: str = "") -> Response:
    """Serve o front construído, com a sessão exigida inclusive nos arquivos.

    Quem chega sem sessão vai para o login, não para um 401: aqui quem bate é navegador de gente,
    diferente de `/painel/api`, que responde JSON para o próprio front tratar.

    Duas coisas que o front precisa e que uma pasta estática comum não dá:

    - **Rota interna recarregada devolve o `index.html`.** `/painel/app/agentes/<id>` não é arquivo
      nenhum; quem sabe dessa rota é o React Router. Sem isto, recarregar a página dá 404.
    - **Nada é servido de fora da pasta.** O caminho é resolvido e conferido contra ela, senão
      `..%2F..%2F.env` viraria leitura de arquivo da VPS.
    """
    if not await servico.sessao_vale(request.cookies.get(COOKIE, "")):
        return RedirectResponse("/painel/entrar", status_code=303)

    pasta = _pasta_do_front()
    indice = pasta / "index.html"
    if not indice.is_file():
        return HTMLResponse(SEM_BUILD, status_code=503)

    if caminho:
        alvo = (pasta / caminho).resolve()
        if alvo.is_file() and alvo.is_relative_to(pasta.resolve()):
            # O nome do arquivo construído leva o hash do conteúdo: mudou o conteúdo, mudou o nome.
            return FileResponse(alvo, headers={"Cache-Control": "public, max-age=31536000, immutable"})

    return FileResponse(indice, headers={"Cache-Control": "no-store"})


router.include_router(api)
router.include_router(api_agentes)
router.include_router(api_conversas)
