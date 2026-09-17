import uuid
from pathlib import Path
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.acessos.servico import usa_acesso
from app.agentes import repo
from app.agentes.modelos import Agente
from app.canais.registro import obter_canal
from app.clientes import repo as clientes_repo
from app.clientes.modelos import Cliente
from app.ia import ferramentas
from app.ia.provedores import modelos_padrao, valida_modelos
from app.plataforma import cripto
from app.plataforma.banco import agora
from app.plataforma.config import config
from app.plataforma.textos import slug

log = structlog.get_logger()

ARQUIVO_PERSONA = "persona.md"
ARQUIVO_RESUMO = "resumo_handoff.md"


class NaoEncontrado(LookupError):
    pass


class Conflito(ValueError):
    pass


class CampoInvalido(ValueError):
    """Mensagem em português, pronta para o menu mostrar."""


CAMPOS_MODELO = ("modelo_conversa", "modelo_fallback", "modelo_auxiliar", "modelo_visao", "modelo_transcricao")
CAMPOS_EDITAVEIS = frozenset(
    {
        "nome",
        "handoff_destino",
        "buffer_segundos",
        "max_mensagens_por_resposta",
        "retomada_automatica_horas",
        "digitacao_caracteres_por_segundo",
        "digitacao_maximo_segundos",
        "ferramentas",
        *CAMPOS_MODELO,
    }
)
PODEM_FICAR_VAZIOS = frozenset({"handoff_destino", "retomada_automatica_horas", "modelo_fallback"})


def _valida_ferramentas(nomes: list[str]) -> list[str]:
    try:
        return ferramentas.valida(nomes)
    except ferramentas.FerramentaDesconhecida as erro:
        raise CampoInvalido(str(erro)) from erro


def _valida_retomada(canal: Any, horas: int | None) -> None:
    if horas is not None and not canal.retoma_por_tempo:
        raise CampoInvalido(
            f"no {canal.nome} o agente volta quando o atendente devolve a conversa; retomada por tempo não se aplica"
        )


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


async def descobrir(sessao: AsyncSession, canal: str, conexao: dict[str, Any]) -> dict[str, Any]:
    """O que o acesso do operador enxerga no canal. Acesso novo que funcionou fica guardado."""
    canal_obj = obter_canal(canal)
    resultado = await usa_acesso(
        sessao, canal_obj, canal_obj.endereco(conexao), conexao,
        lambda acesso: canal_obj.descobrir({**conexao, **acesso}),
    )
    await sessao.commit()
    return resultado


async def criar_agente(
    sessao: AsyncSession,
    cliente_id: uuid.UUID,
    nome: str,
    canal: str,
    conexao: dict[str, Any],
    modelos: dict[str, str | None] | None = None,
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
    opcoes["handoff_destino"] = canal_obj.valida_destino_handoff(opcoes.get("handoff_destino"))
    _valida_retomada(canal_obj, opcoes.get("retomada_automatica_horas"))
    if opcoes.get("ferramentas") is not None:
        opcoes["ferramentas"] = _valida_ferramentas(opcoes["ferramentas"])
    token = cripto.novo_token()
    acesso: dict[str, Any] = {}

    async def conecta(informado: dict[str, Any]) -> dict[str, Any]:
        acesso.update(informado)
        return await canal_obj.conectar({**conexao, **informado}, config().url_webhook(canal, token), nome)

    credenciais_ok = await usa_acesso(sessao, canal_obj, canal_obj.endereco(conexao), conexao, conecta)

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
            await canal_obj.desconectar({**conexao, **acesso}, credenciais_ok)
        except Exception as erro:
            log.error("desconectar_falhou", canal=canal, erro=repr(erro))
        raise
    return agente, token


async def editar_agente(
    sessao: AsyncSession,
    cliente_id: uuid.UUID,
    agente_id: uuid.UUID,
    campos: dict[str, Any],
    acesso: dict[str, Any] | None = None,
    no_canal: bool = True,
) -> Agente:
    """Altera só os campos enviados. O slug e a pasta de prompts não mudam com o nome.

    Com `no_canal`, o nome novo também vai para o canal (no Chatwoot, o nome do bot), com o acesso
    informado ou o guardado; se o canal recusar, nada é salvo. Vale na próxima mensagem: webhook e
    turno releem o agente.
    """
    agente = await repo.obter(sessao, cliente_id, agente_id)
    if agente is None:
        raise NaoEncontrado("agente não encontrado")
    desconhecidos = set(campos) - CAMPOS_EDITAVEIS
    if desconhecidos:
        raise CampoInvalido(f"campos que não podem ser editados: {', '.join(sorted(desconhecidos))}")
    vazios = sorted(c for c, v in campos.items() if v is None and c not in PODEM_FICAR_VAZIOS)
    if vazios:
        raise CampoInvalido(f"campos obrigatórios não podem ficar vazios: {', '.join(vazios)}")

    canal = obter_canal(agente.canal)
    if "nome" in campos:
        campos["nome"] = campos["nome"].strip()
        if not campos["nome"]:
            raise CampoInvalido("nome do agente vazio")
    if "handoff_destino" in campos:
        campos["handoff_destino"] = canal.valida_destino_handoff(campos["handoff_destino"])
    if "retomada_automatica_horas" in campos:
        _valida_retomada(canal, campos["retomada_automatica_horas"])
    valida_modelos({c: v for c, v in campos.items() if c in CAMPOS_MODELO})
    if "ferramentas" in campos:
        campos["ferramentas"] = _valida_ferramentas(campos["ferramentas"])
    if no_canal and "nome" in campos and campos["nome"] != agente.nome:
        cred = credenciais(agente)
        await usa_acesso(
            sessao, canal, canal.endereco(cred), acesso,
            lambda a: canal.renomear(a, cred, campos["nome"]),
        )

    for campo, valor in campos.items():
        setattr(agente, campo, valor)
    await sessao.commit()
    log.info("agente_editado", agente_id=str(agente.id), campos=sorted(campos))
    return agente


async def remover_agente(
    sessao: AsyncSession,
    cliente_id: uuid.UUID,
    agente_id: uuid.UUID,
    confirmacao: str,
    acesso: dict[str, Any] | None = None,
    no_canal: bool = True,
) -> bool:
    """Exclusão lógica: webhook invalidado e credenciais apagadas. Conversas e consumo ficam.

    `confirmacao` é o nome atual do agente (ou o de quando foi criado, que deu o slug). Com
    `no_canal`, desfaz a conexão no canal antes (no Chatwoot, apaga o Agent Bot), com o acesso
    informado ou o guardado; se o canal recusar, nada é removido. Devolve se desfez.
    """
    agente = await repo.obter(sessao, cliente_id, agente_id)
    if agente is None:
        raise NaoEncontrado("agente não encontrado")
    if slug(confirmacao) not in (agente.slug, slug(agente.nome)):
        raise CampoInvalido(f"confirmação não confere: digite o nome do agente, {agente.nome}")

    desconectado = False
    if no_canal:
        canal = obter_canal(agente.canal)
        cred = credenciais(agente)
        await usa_acesso(
            sessao, canal, canal.endereco(cred), acesso, lambda a: canal.desconectar(a, cred)
        )
        desconectado = True

    # Slug liberado: um agente novo com o mesmo nome reaproveita a pasta de prompts.
    agente.slug = f"{agente.slug}~removido-{agente.id.hex[:8]}"
    agente.ativo = False
    agente.removido_em = agora()
    agente.credenciais_cifradas = cripto.cifra({})
    agente.token_webhook_hash = cripto.hash_token(cripto.novo_token())
    agente.token_webhook_cifrado = ""
    await sessao.commit()
    log.info("agente_removido", agente_id=str(agente.id), desconectado=desconectado)
    return desconectado


def url_webhook(agente: Agente) -> str:
    return config().url_webhook(agente.canal, cripto.decifra_texto(agente.token_webhook_cifrado))


def credenciais(agente: Agente) -> dict[str, Any]:
    return cripto.decifra(agente.credenciais_cifradas)
