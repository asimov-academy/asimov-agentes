import uuid
from pathlib import Path
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.agentes import repo
from app.agentes.modelos import Agente
from app.canais.registro import obter_canal
from app.clientes import repo as clientes_repo
from app.clientes.modelos import Cliente
from app.ia.provedores import modelos_padrao, valida_modelos
from app.plataforma import cripto
from app.plataforma.config import config
from app.plataforma.textos import slug

log = structlog.get_logger()

ARQUIVO_PERSONA = "persona.md"
ARQUIVO_RESUMO = "resumo_handoff.md"


class NaoEncontrado(LookupError):
    pass


class Conflito(ValueError):
    pass


def _cria_prompts(cliente: Cliente, nome_agente: str, slug_agente: str) -> tuple[str, str]:
    """Copia os prompts padrão para a pasta do agente. Nunca sobrescreve um prompt editado."""
    cfg = config()
    relativa = Path(cliente.slug) / slug_agente
    pasta = cfg.diretorio_prompts / relativa
    pasta.mkdir(parents=True, exist_ok=True)
    for arquivo in (ARQUIVO_PERSONA, ARQUIVO_RESUMO):
        destino = pasta / arquivo
        if destino.exists():
            continue
        modelo = (cfg.diretorio_modelos / "prompts" / arquivo).read_text(encoding="utf-8")
        destino.write_text(
            modelo.replace("{{AGENTE}}", nome_agente).replace("{{CLIENTE}}", cliente.nome),
            encoding="utf-8",
        )
    return str(relativa / ARQUIVO_PERSONA), str(relativa / ARQUIVO_RESUMO)


async def criar_agente(
    sessao: AsyncSession,
    cliente_id: uuid.UUID,
    nome: str,
    canal: str,
    conexao: dict[str, Any],
    modelos: dict[str, str] | None = None,
    **opcoes: Any,
) -> tuple[Agente, str]:
    """Conecta o canal ao webhook do agente e grava o agente.

    Devolve o agente e o token do webhook, que só existe em claro neste momento. Se a gravação
    falhar depois de o canal ser conectado, a conexão é desfeita.
    """
    cliente = await clientes_repo.obter(sessao, cliente_id)
    if cliente is None:
        raise NaoEncontrado("cliente não encontrado")

    nome = nome.strip()
    slug_agente = slug(nome)
    if await repo.slug_existe(sessao, cliente_id, slug_agente):
        raise Conflito(f"o cliente já tem um agente {slug_agente!r}")

    modelos_finais = {**modelos_padrao(), **(modelos or {})}
    valida_modelos(modelos_finais)

    canal_obj = obter_canal(canal)
    token = cripto.novo_token()
    credenciais_ok = await canal_obj.conectar(conexao, config().url_webhook(canal, token), nome)

    try:
        arquivo_prompt, arquivo_resumo = _cria_prompts(cliente, nome, slug_agente)
        agente = Agente(
            cliente_id=cliente.id,
            nome=nome,
            slug=slug_agente,
            canal=canal,
            credenciais_cifradas=cripto.cifra(credenciais_ok),
            token_webhook_hash=cripto.hash_token(token),
            token_webhook_cifrado=cripto.cifra_texto(token),
            arquivo_prompt=arquivo_prompt,
            arquivo_prompt_handoff=arquivo_resumo,
            **modelos_finais,
            **{k: v for k, v in opcoes.items() if v is not None},
        )
        await repo.criar(sessao, agente)
        await sessao.commit()
    except Exception:
        await sessao.rollback()
        try:
            await canal_obj.desconectar(conexao, credenciais_ok)
        except Exception as erro:
            log.error("desconectar_falhou", canal=canal, erro=repr(erro))
        raise
    return agente, token


def url_webhook(agente: Agente) -> str:
    return config().url_webhook(agente.canal, cripto.decifra_texto(agente.token_webhook_cifrado))


def credenciais(agente: Agente) -> dict[str, Any]:
    return cripto.decifra(agente.credenciais_cifradas)
