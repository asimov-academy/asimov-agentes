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
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from redis.asyncio import Redis

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
