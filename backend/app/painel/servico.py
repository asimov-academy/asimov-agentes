"""Senha, código de primeiro acesso, sessão e freio de tentativa do painel.

Três decisões que valem explicar:

- **A senha usa `hashlib.scrypt`, da biblioteca padrão.** Não entra dependência nova só para
  guardar uma senha, do mesmo jeito que o ícone do app é escrito com `zlib` e o estado do setup é
  um arquivo `CHAVE=VALOR`. Os parâmetros ficam gravados junto do hash, então subir o custo depois
  não invalida a senha de ninguém.
- **A sessão mora no Redis, não no banco.** Expira sozinha, some quando o operador sai e não deixa
  lixo para limpar. O Redis já sobe com `appendonly yes`, então reiniciar não derruba a sessão.
- **O primeiro acesso exige um código de uso único**, mostrado por `asimov painel` no terminal da
  VPS. Sem ele não há como criar a conta: quem achar o endereço antes do operador não vira dono do
  painel.
"""

import hashlib
import hmac
import secrets
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.consumo import repo as consumo_repo
from app.painel import repo
from app.plataforma.banco import agora
from app.plataforma.config import config

# Custo do scrypt. n=2^14 com r=8 usa 16 MB e uns 50 ms num vCPU de VPS: caro para quem tenta
# adivinhar e imperceptível para quem entra uma vez por dia. Subir o n multiplica a memória por
# tentativa, e a VPS mais barata do projeto tem 2 GB.
# O `maxmem` precisa ser passado: o padrão do OpenSSL é 32 MB e recusa o cálculo sem explicação.
SCRYPT_N = 1 << 14
SCRYPT_R = 8
SCRYPT_P = 1
SCRYPT_MAXMEM = 64 * 1024 * 1024

DURACAO_SESSAO_SEGUNDOS = 12 * 3600
DURACAO_CODIGO_SEGUNDOS = 15 * 60
ERROS_ANTES_DA_ESPERA = 5
ESPERA_SEGUNDOS = 15 * 60
TAMANHO_MINIMO_SENHA = 12


@asynccontextmanager
async def conexao() -> AsyncIterator[Redis]:
    cliente = Redis.from_url(config().redis_url)
    try:
        yield cliente
    finally:
        await cliente.aclose()


# Senha


def cifra_senha(senha: str) -> str:
    sal = secrets.token_bytes(16)
    bruto = hashlib.scrypt(
        senha.encode(), salt=sal, n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P, maxmem=SCRYPT_MAXMEM
    )
    return f"scrypt${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}${sal.hex()}${bruto.hex()}"


def confere_senha(senha: str, guardado: str) -> bool:
    try:
        algoritmo, n, r, p, sal, bruto = guardado.split("$")
        if algoritmo != "scrypt":
            return False
        calculado = hashlib.scrypt(
            senha.encode(),
            salt=bytes.fromhex(sal),
            n=int(n),
            r=int(r),
            p=int(p),
            maxmem=SCRYPT_MAXMEM,
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(calculado.hex(), bruto)


def senha_fraca(senha: str) -> str:
    """Devolve o motivo, ou vazio quando a senha serve."""
    if len(senha) < TAMANHO_MINIMO_SENHA:
        return f"A senha precisa de pelo menos {TAMANHO_MINIMO_SENHA} caracteres."
    if senha.isdigit():
        return "Só números é fácil de adivinhar; misture letras."
    return ""


# Código de primeiro acesso


def _chave_codigo(codigo: str) -> str:
    """Guarda o hash, não o código: quem ler o Redis não entra com ele."""
    return "painel:codigo:" + hashlib.sha256(codigo.encode()).hexdigest()


def novo_codigo() -> str:
    letras = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # sem I, O, 0 e 1, que se confundem no terminal
    sorteio = "".join(secrets.choice(letras) for _ in range(8))
    return f"{sorteio[:4]}-{sorteio[4:]}"


async def guarda_codigo(codigo: str) -> None:
    async with conexao() as r:
        await r.setex(_chave_codigo(codigo), DURACAO_CODIGO_SEGUNDOS, "1")


def _normaliza(codigo: str) -> str:
    return codigo.strip().upper()


async def codigo_vale(codigo: str) -> bool:
    """Confere sem gastar: o código só é consumido depois de a conta existir de verdade.

    Gastar antes deixava o operador sem código e sem conta quando a criação falhava no meio
    (revisão da auditoria de 2026-09-18).
    """
    async with conexao() as r:
        return bool(await r.exists(_chave_codigo(_normaliza(codigo))))


async def gasta_codigo(codigo: str) -> bool:
    """Confere e apaga no mesmo passo: o código vale uma vez só."""
    async with conexao() as r:
        return bool(await r.delete(_chave_codigo(_normaliza(codigo))))


# Sessão


def _chave_sessao(token: str) -> str:
    return "painel:sessao:" + hashlib.sha256(token.encode()).hexdigest()


async def abre_sessao() -> str:
    token = secrets.token_urlsafe(32)
    async with conexao() as r:
        await r.setex(_chave_sessao(token), DURACAO_SESSAO_SEGUNDOS, "operador")
    return token


async def sessao_vale(token: str) -> bool:
    """Renova o prazo a cada uso: quem está mexendo no painel não é deslogado no meio."""
    if not token:
        return False
    async with conexao() as r:
        chave = _chave_sessao(token)
        if not await r.exists(chave):
            return False
        await r.expire(chave, DURACAO_SESSAO_SEGUNDOS)
        return True


async def fecha_sessao(token: str) -> None:
    if not token:
        return
    async with conexao() as r:
        await r.delete(_chave_sessao(token))


# Freio de tentativa


def _chave_erros(de_onde: str) -> str:
    return f"painel:erros:{de_onde}"


async def em_espera(de_onde: str) -> bool:
    async with conexao() as r:
        erros = await r.get(_chave_erros(de_onde))
    return int(erros or 0) >= ERROS_ANTES_DA_ESPERA


async def erro_de_senha(de_onde: str) -> int:
    """Conta o erro e devolve quantas tentativas restam antes da espera."""
    async with conexao() as r:
        erros = await r.incr(_chave_erros(de_onde))
        await r.expire(_chave_erros(de_onde), ESPERA_SEGUNDOS)
    return max(0, ERROS_ANTES_DA_ESPERA - int(erros))


async def limpa_erros(de_onde: str) -> None:
    async with conexao() as r:
        await r.delete(_chave_erros(de_onde))


# Token de escrita do front (CSRF)


def token_csrf(token_sessao: str) -> str:
    """Derivado da sessão, não guardado em lugar nenhum.

    O cookie é `HttpOnly`, então o JavaScript não lê o token da sessão: o único jeito de o front
    conhecer este valor é ter chamado `GET /painel/api/eu` com a sessão válida. Site de terceiro
    consegue disparar um pedido com o cookie, mas não consegue ler a resposta, e portanto não tem o
    cabeçalho. Derivar com HMAC evita mais uma chave no Redis por sessão.
    """
    return hmac.new(
        config().chave_criptografia.encode(), b"csrf:" + token_sessao.encode(), hashlib.sha256
    ).hexdigest()


def csrf_confere(token_sessao: str, cabecalho: str) -> bool:
    if not token_sessao or not cabecalho:
        return False
    return hmac.compare_digest(token_csrf(token_sessao), cabecalho)


# Visão geral
#
# Monta a tela de abertura a partir das leituras do `repo.py` e do relatório de consumo que o menu
# do terminal já usa. Nenhuma regra nova nasce aqui: é composição, para a rota não orquestrar.

PERIODOS = {1: "hour", 7: "day", 30: "day"}
"""Períodos que a tela oferece e a fatia do gráfico em cada um. Hoje sai por hora."""


def resumo_da_falha(detalhe: dict[str, Any] | None) -> str:
    """O resumo curto da falha, que é o único pedaço do detalhe que sai do backend.

    O detalhe guarda o que o provedor respondeu, e o corpo de um erro de provedor já veio com a
    chave de API dentro. Mandar o dicionário inteiro para o navegador põe segredo numa tela. Sai só
    o `erro` ou os `problemas`, numa linha e cortado, que é o mesmo que o menu do terminal mostra.
    """
    bruto = (detalhe or {}).get("erro") or (detalhe or {}).get("problemas") or ""
    return " ".join(str(bruto).split())[:200]


def _situacao(falhas: list[dict[str, Any]], handoffs: list[dict[str, Any]]) -> dict[str, str]:
    """Verde, amarelo ou vermelho para a barra do topo.

    O `asimov diagnostico` pergunta o código HTTP de cada endereço, coisa que só o terminal da VPS
    consegue fazer por dentro. Aqui a mesma pergunta é respondida pelo que a API sabe: canal fora
    do ar é vermelho, outra falha recente ou handoff vencido é amarelo. Registrado em
    spec/decisoes.md.
    """
    vencidos = [h for h in handoffs if h["vencido"]]
    fora_do_ar = [f for f in falhas if f["tipo"] == "canal_fora_do_ar"]
    if fora_do_ar:
        return {"cor": "perigo", "texto": "canal fora do ar"}
    # Texto curto: ele mora no rodapé do menu lateral, que tem uns 200px de largura.
    if falhas and vencidos:
        return {"cor": "atencao", "texto": f"{len(falhas)} falhas · {len(vencidos)} vencidos"}
    if falhas:
        return {"cor": "atencao", "texto": f"{len(falhas)} falhas"}
    if vencidos:
        return {"cor": "atencao", "texto": f"{len(vencidos)} handoffs vencidos"}
    return {"cor": "ok", "texto": "tudo no ar"}


def _serie_cheia(
    linhas: list[dict[str, Any]], desde: datetime, ate: datetime, por: str
) -> list[dict[str, Any]]:
    """Dia (ou hora) sem turno vira zero: gráfico com buraco mente sobre o ritmo."""
    passo = timedelta(hours=1) if por == "hour" else timedelta(days=1)
    # A consulta devolve a fatia sem fuso, já em UTC; aqui ela volta a ser hora de verdade.
    por_fatia = {linha["quando"].replace(tzinfo=UTC): linha["turnos"] for linha in linhas}
    quando = desde.astimezone(UTC).replace(minute=0, second=0, microsecond=0)
    if por == "day":
        quando = quando.replace(hour=0)
    saida: list[dict[str, Any]] = []
    while quando <= ate:
        saida.append({"quando": quando, "turnos": por_fatia.get(quando, 0)})
        quando += passo
    return saida


def _variacao(agora_: Any, antes: Any) -> float | None:
    """Quanto o número mudou do período anterior para este, em por cento.

    Sem base de comparação (o período anterior foi zero) a resposta é `None`, e a tela escreve
    "sem comparação" em vez de inventar um "+100%" que não quer dizer nada.
    """
    antes = Decimal(antes)
    if antes == 0:
        return None
    return float((Decimal(agora_) - antes) / antes * 100)


async def visao_geral(
    sessao: AsyncSession, dias: int, cliente_id: uuid.UUID | None = None
) -> dict[str, Any]:
    """Cartões do período, gráfico de turnos, gasto por modelo, últimas falhas e handoffs abertos.

    Todo número vem com o mesmo número do período anterior do lado: é o que transforma "407 turnos"
    em "407 turnos, 18% mais que na semana passada".
    """
    por = PERIODOS[dias]
    ate = agora()
    desde = ate - timedelta(days=dias)
    comeco_anterior = desde - timedelta(days=dias)

    totais = await repo.totais(sessao, desde, cliente_id)
    antes = await repo.totais(sessao, comeco_anterior, cliente_id, ate=desde)
    serie = await repo.serie_de_turnos(sessao, desde, por, cliente_id)
    modelos = await repo.gasto_por_modelo(sessao, desde, cliente_id)
    resolucao = await repo.resolucao(sessao, desde, cliente_id)
    handoffs = [
        dict(h, vencido=h["retomar_em"] is not None and h["retomar_em"] <= ate)
        for h in await repo.handoffs_abertos(sessao, cliente_id)
    ]
    por_agente, falhas = (
        await consumo_repo.consumo_de_todos_os_clientes(sessao, desde)
        if cliente_id is None
        else await consumo_repo.consumo(sessao, cliente_id, desde)
    )

    # O detalhe cru nunca sai daqui: vira o mesmo resumo curto do terminal.
    falhas = [dict(f, resumo=resumo_da_falha(f.pop("detalhe", None))) for f in falhas]

    return {
        "dias": dias,
        "desde": desde,
        "totais": dict(totais, handoffs_vencidos=len([h for h in handoffs if h["vencido"]])),
        "variacao": {
            campo: _variacao(totais[campo], antes[campo])
            for campo in ("conversas", "turnos", "custo", "falhas")
        },
        "serie": {"por": por, "pontos": _serie_cheia(serie, desde, ate, por)},
        "modelos": modelos,
        "resolucao": dict(
            resolucao,
            sozinho=resolucao["conversas"] - resolucao["com_gente"],
            porcento=round(
                (resolucao["conversas"] - resolucao["com_gente"]) / resolucao["conversas"] * 100
            )
            if resolucao["conversas"]
            else None,
        ),
        "agentes": sorted(
            (
                {
                    "agente": linha["agente"],
                    "cliente": linha["cliente"],
                    "turnos": linha["turnos"],
                    "custo": linha["custo_estimado"],
                }
                for linha in por_agente
            ),
            key=lambda a: a["turnos"],
            reverse=True,
        )[:6],
        "falhas": falhas,
        "handoffs": sorted(handoffs, key=lambda h: (not h["vencido"], h["iniciado_em"])),
        "situacao": _situacao(falhas, handoffs),
    }
