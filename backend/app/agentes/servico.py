import uuid
from pathlib import Path
from typing import TYPE_CHECKING, Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.acessos.servico import usa_acesso
from app.agentes import repo
from app.agentes.modelos import Agente
from app.canais.base import Canal
from app.canais.registro import obter_canal
from app.conversas import divisao
from app.clientes import repo as clientes_repo
from app.clientes.modelos import Cliente
from app.ia import ferramentas
from app.ia import chaves
from app.ia.provedores import valida_modelos
from app.plataforma import cripto
from app.plataforma.banco import agora
from app.plataforma.config import config
from app.plataforma.textos import slug, so_digitos

if TYPE_CHECKING:
    from app.conversas.modelos import Conversa

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
        "ritmo",
        "ferramentas",
        "emojis",
        "tom",
        "transfere_para_humano",
        "restringe_temas",
        "memoria_ativa",
        "contatos_permitidos",
        *CAMPOS_MODELO,
    }
)
PODEM_FICAR_VAZIOS = frozenset({"handoff_destino", "retomada_automatica_horas", "modelo_fallback"})
MAXIMO_CONTATOS_PERMITIDOS = 20


def _valida_contatos(numeros: list[str]) -> list[str]:
    """Guarda só dígitos: o operador digita com máscara e o canal manda de outro jeito."""
    if len(numeros) > MAXIMO_CONTATOS_PERMITIDOS:
        raise CampoInvalido(
            f"lista de quem pode falar com o agente tem no máximo {MAXIMO_CONTATOS_PERMITIDOS} números"
        )
    limpos = []
    for numero in numeros:
        digitos = so_digitos(numero)
        if len(digitos) < 8:
            raise CampoInvalido(f"número inválido na lista: {numero!r}")
        if digitos not in limpos:
            limpos.append(digitos)
    return limpos


TONS = ("formal", "normal", "descontraido")


def _valida_tom(tom: Any) -> str:
    if tom not in TONS:
        raise CampoInvalido(f"tom precisa ser um de: {', '.join(TONS)}")
    return str(tom)


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


ARQUIVO_DONO = ".cliente"


def _pasta_do_cliente(cliente: Cliente) -> Path:
    """Pasta de prompts do cliente, nunca a de outro que teve o mesmo nome.

    O slug volta a ficar livre quando uma empresa é removida, e os arquivos de prompt ficam no
    disco de propósito (prompt editado não se apaga sozinho). Sem dono marcado, a empresa nova com
    o mesmo nome herdava as instruções da antiga (auditoria de 2026-09-18, A05).

    O dono fica em `.cliente`, dentro da pasta. Quando o dono é outro, quem sai é a pasta antiga,
    que vai para `<slug>-<8 do dono antigo>`: a empresa viva fica sempre em `<slug>/<agente>`,
    porque esse caminho também é a URL pública da política de privacidade. Pasta anterior a esta
    regra não tem o arquivo e é adotada por quem a estiver usando: instalação no ar não muda.
    """
    pasta = config().diretorio_prompts / cliente.slug
    marca = pasta / ARQUIVO_DONO
    if not pasta.exists():
        pasta.mkdir(parents=True, exist_ok=True)
        marca.write_text(str(cliente.id), encoding="utf-8")
        return pasta
    dono = marca.read_text(encoding="utf-8").strip() if marca.exists() else ""
    if dono in ("", str(cliente.id)):
        marca.write_text(str(cliente.id), encoding="utf-8")
        return pasta

    guardada = config().diretorio_prompts / f"{cliente.slug}-{dono[:8]}"
    sufixo = 2
    while guardada.exists():
        guardada = config().diretorio_prompts / f"{cliente.slug}-{dono[:8]}-{sufixo}"
        sufixo += 1
    pasta.rename(guardada)
    log.info("prompts_da_empresa_anterior_guardados", pasta=guardada.name)
    pasta.mkdir(parents=True, exist_ok=True)
    marca.write_text(str(cliente.id), encoding="utf-8")
    return pasta


def _cria_prompts(cliente: Cliente, nome_agente: str, slug_agente: str) -> tuple[str, str]:
    """Copia os prompts padrão para a pasta do agente. Nunca sobrescreve um prompt editado."""
    cfg = config()
    relativa = Path(_pasta_do_cliente(cliente).name) / slug_agente
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

    await chaves.carregar(sessao)
    modelos_finais = chaves.completa(modelos or {})
    valida_modelos(modelos_finais)

    canal_obj = obter_canal(canal)
    opcoes["handoff_destino"] = canal_obj.valida_destino_handoff(opcoes.get("handoff_destino"))
    _valida_retomada(canal_obj, opcoes.get("retomada_automatica_horas"))
    if opcoes.get("ferramentas") is not None:
        opcoes["ferramentas"] = _valida_ferramentas(opcoes["ferramentas"])
    if opcoes.get("tom") is not None:
        opcoes["tom"] = _valida_tom(opcoes["tom"])
    if opcoes.get("contatos_permitidos") is not None:
        opcoes["contatos_permitidos"] = _valida_contatos(opcoes["contatos_permitidos"])
    opcoes = {c: v for c, v in opcoes.items() if v is not None}
    opcoes.update(_ritmo(opcoes, divisao.RITMOS["natural"]))
    token = cripto.novo_token()
    acesso: dict[str, Any] = {}

    async def conecta(informado: dict[str, Any]) -> dict[str, Any]:
        acesso.update(informado)
        return await canal_obj.conectar(
            {**conexao, **informado}, _url_webhook(canal_obj, canal, token), nome
        )

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


async def conectar_canal(
    sessao: AsyncSession,
    cliente_id: uuid.UUID,
    agente_id: uuid.UUID,
    canal: str,
    conexao: dict[str, Any],
    handoff_destino: dict[str, Any] | None,
    retomada_automatica_horas: int | None = None,
) -> Agente:
    """Liga num canal externo um agente criado sem canal (nativo).

    Prompt, modelos, ajustes e conversas ficam; o webhook passa a ser o do canal novo, com o mesmo
    token. As conversas de teste do terminal continuam no nativo. Se a gravação falhar depois de
    conectar, a conexão é desfeita.
    """
    agente = await repo.obter(sessao, cliente_id, agente_id)
    if agente is None or not agente.ativo:
        raise NaoEncontrado("agente não encontrado")
    if obter_canal(agente.canal).externo:
        raise Conflito(
            f"o agente já está no {agente.canal}; para trocar de canal, remova e crie de novo (o prompt volta junto)"
        )
    novo = obter_canal(canal)
    if not novo.externo:
        raise CampoInvalido(f"{canal} não é um canal para ligar o agente")
    destino = novo.valida_destino_handoff(handoff_destino)
    _valida_retomada(novo, retomada_automatica_horas)
    token = cripto.decifra_texto(agente.token_webhook_cifrado)
    acesso: dict[str, Any] = {}

    async def conecta(informado: dict[str, Any]) -> dict[str, Any]:
        acesso.update(informado)
        return await novo.conectar(
            {**conexao, **informado}, _url_webhook(novo, canal, token), agente.nome
        )

    credenciais_ok = await usa_acesso(sessao, novo, novo.endereco(conexao), conexao, conecta)
    try:
        agente.canal = canal
        agente.credenciais_cifradas = cripto.cifra(credenciais_ok)
        agente.handoff_destino = destino
        agente.retomada_automatica_horas = retomada_automatica_horas
        await sessao.commit()
    except Exception:
        await sessao.rollback()
        try:
            await novo.desconectar({**conexao, **acesso}, credenciais_ok)
        except Exception as erro:
            log.error("desconectar_falhou", canal=canal, erro=repr(erro))
        raise
    log.info("agente_conectado", agente_id=str(agente.id), canal=canal)
    return agente


def _ritmo(campos: dict[str, Any], atuais: dict[str, int]) -> dict[str, Any]:
    """Preset escreve os números; números que não batem com preset nenhum viram `manual`.

    Guardar os dois evita a pergunta "quem manda": o ritmo é um atalho que escreve, e o que o turno
    lê continua sendo o número. O nome sai sempre dos números finais, senão a tela diria "Natural"
    para um agente que não digita como o Natural.
    """
    if "ritmo" in campos:
        if campos["ritmo"] not in {*divisao.RITMOS, "manual"}:
            raise CampoInvalido(f"ritmo desconhecido: {campos['ritmo']}")
        return divisao.numeros_do_ritmo(campos["ritmo"])
    if not any(campo in campos for campo in divisao.CAMPOS_DO_RITMO):
        return {}
    finais = {campo: campos.get(campo, atuais.get(campo)) for campo in divisao.CAMPOS_DO_RITMO}
    return {"ritmo": divisao.ritmo_dos_numeros(finais)}


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
    await chaves.carregar(sessao)
    valida_modelos({c: v for c, v in campos.items() if c in CAMPOS_MODELO})
    if "ferramentas" in campos:
        campos["ferramentas"] = _valida_ferramentas(campos["ferramentas"])
    if "tom" in campos:
        campos["tom"] = _valida_tom(campos["tom"])
    campos.update(_ritmo(campos, {c: getattr(agente, c) for c in divisao.CAMPOS_DO_RITMO}))
    if "contatos_permitidos" in campos:
        campos["contatos_permitidos"] = _valida_contatos(campos["contatos_permitidos"] or [])
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


def url_privacidade(agente: Agente) -> str:
    """URL pública da política de privacidade deste agente, que o app da Meta dele pede.

    O slug da empresa sai de `arquivo_prompt` (`<empresa>/<agente>/persona.md`), que já carrega os
    dois: assim a saída da API não precisa de uma consulta a mais só para montar um endereço.
    """
    empresa = Path(agente.arquivo_prompt).parts[0]
    return f"{config().url_publica()}/privacidade/{empresa}/{agente.slug}"


def url_webhook(agente: Agente) -> str:
    return _url_webhook(obter_canal(agente.canal), agente.canal, cripto.decifra_texto(agente.token_webhook_cifrado))


def _url_webhook(canal_obj: Canal, canal: str, token: str) -> str:
    """Canal que roda na própria VPS (WAHA) chama a API pela rede do Compose, sem sair para fora."""
    cfg = config()
    if canal_obj.webhook_interno:
        return cfg.url_webhook_interna(canal, token)
    return cfg.url_webhook(canal, token)


def credenciais(agente: Agente) -> dict[str, Any]:
    return cripto.decifra(agente.credenciais_cifradas)


def canal_da_conversa(agente: Agente, conversa: "Conversa") -> tuple[Canal, dict[str, Any]]:
    """A conversa de teste no terminal fala pelo canal nativo, qualquer que seja o canal do agente.

    As credenciais do agente só servem ao canal dele.
    """
    canal = obter_canal(conversa.canal)
    return canal, credenciais(agente) if conversa.canal == agente.canal else {}


# Perfil e prompt
#
# A aba Trabalho do painel pergunta em português o que o agente faz, para quem e sobre qual empresa,
# e daqui sai o `persona.md`. O arquivo continua sendo a fonte do prompt de sistema: o formulário só
# escreve nele. Editar à mão continua valendo, e salvar o formulário reescreve o texto (o painel
# avisa antes).

FUNCOES = {
    "suporte": "resolve problemas de quem já é cliente",
    "vendas": "ajuda quem está decidindo a comprar",
    "atendimento": "atende quem chega, tira dúvidas e encaminha",
}


def monta_persona(agente: Agente, empresa: str) -> str:
    """Escreve o `persona.md` a partir do perfil. Sem perfil, devolve a linha do modelo.

    Texto curto de propósito: prompt grande custa token em todo turno, e a v0.8.11 mostrou a
    diferença (uns 550 tokens por turno no agente cru contra uns 5.600 com tudo ligado).
    """
    perfil = agente.perfil or {}
    if not perfil.get("funcao"):
        return f"Você é {agente.nome}, do atendimento de {empresa}.\n"

    linhas = [f"Você é {agente.nome}, de {empresa}, e {FUNCOES[perfil['funcao']]}."]
    if perfil.get("publico"):
        linhas.append(f"Quem fala com você: {perfil['publico']}.")
    if perfil.get("sobre_empresa"):
        linhas += ["", f"Sobre {empresa}:", perfil["sobre_empresa"].strip()]
    if perfil.get("site"):
        linhas.append(f"Site: {perfil['site']}")
    nunca = [linha.strip(" -\t") for linha in (perfil.get("nunca_dizer") or "").splitlines()]
    nunca = [linha for linha in nunca if linha]
    if nunca:
        # Entra como regra da empresa, e não como exemplo: o modelo repete o que vê como exemplo.
        linhas += ["", "Nunca diga, em nenhuma hipótese:"]
        linhas += [f"- {linha}" for linha in nunca[:20]]
    if agente.assina_nome:
        linhas += ["", f"Assine as respostas com o seu nome, {agente.nome}."]
    return "\n".join(linhas) + "\n"


def caminho_do_prompt(agente: Agente) -> Path:
    return config().diretorio_prompts / agente.arquivo_prompt


def le_prompt_do_agente(agente: Agente) -> str:
    """O texto que o modelo recebe hoje. Arquivo sumido não derruba a tela do painel."""
    caminho = caminho_do_prompt(agente)
    return caminho.read_text(encoding="utf-8") if caminho.exists() else ""


def escreve_prompt_do_agente(agente: Agente, texto: str) -> None:
    caminho = caminho_do_prompt(agente)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(texto, encoding="utf-8")
    log.info("prompt_escrito", agente_id=str(agente.id))


async def grava_perfil(
    sessao: AsyncSession,
    cliente_id: uuid.UUID,
    agente_id: uuid.UUID,
    perfil: dict[str, Any],
    assina_nome: bool | None = None,
) -> tuple[Agente, str]:
    """Guarda o perfil e reescreve o `persona.md`. Devolve o agente e o prompt que ficou no disco."""
    agente = await repo.obter(sessao, cliente_id, agente_id)
    if agente is None:
        raise NaoEncontrado("agente não encontrado")
    funcao = perfil.get("funcao")
    if funcao is not None and funcao not in FUNCOES:
        raise CampoInvalido(f"função desconhecida: {funcao}")

    cliente = await clientes_repo.obter(sessao, cliente_id)
    agente.perfil = {**(agente.perfil or {}), **perfil}
    if assina_nome is not None:
        agente.assina_nome = assina_nome
    texto = monta_persona(agente, cliente.nome if cliente else "")
    escreve_prompt_do_agente(agente, texto)
    await sessao.commit()
    await sessao.refresh(agente)
    return agente, texto
