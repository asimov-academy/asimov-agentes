"""Rotas de agente do painel: lista, criação, ficha, edição e remoção.

Mesma fronteira do `api.py`: nada de `/admin` publicado, nenhuma regra de negócio nova. Tudo aqui
chama o `agentes/servico.py` que o menu do terminal já chama, para o painel e o terminal nunca
divergirem no que fazem.

O `cliente_id` das rotas de um agente sai da própria linha lida do banco, não do corpo. As rotas que
criam recebem a empresa na URL, conferida antes de virar filtro.
"""

import uuid
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.acessos.servico import AcessoNecessario
from app.agentes import servico as agentes_servico
from app.agentes.modelos import Agente
from app.canais.base import CredencialInvalida, DestinoInvalido
from app.canais.nativo import servico as nativo_servico
from app.canais.registro import CANAIS, credenciais_visiveis, obter_canal
from app.clientes import repo as clientes_repo
from app.clientes import servico as clientes_servico
from app.ia import chaves, ferramentas
from app.ia.provedores import PROVEDORES, PROVEDORES_TRANSCRICAO, ModeloInvalido
from app.painel import canais as canais_do_painel
from app.painel import repo
from app.painel.acesso import exige_csrf, exige_sessao
from app.plataforma.banco import sessao
from app.plataforma.config import config

router = APIRouter(
    prefix="/api",
    include_in_schema=False,
    dependencies=[Depends(exige_sessao), Depends(exige_csrf)],
)


class AgenteDoPainel(BaseModel):
    """O agente como a lista e o popup precisam dele.

    Credencial de canal sai sempre pela `credenciais_visiveis`, que é a mesma máscara do menu: o
    que está cifrado no banco não vira JSON nem para o operador.
    """

    id: uuid.UUID
    cliente_id: uuid.UUID
    empresa: str
    nome: str
    slug: str
    canal: str
    ativo: bool
    criado_em: str
    url_webhook: str | None
    """Só na ficha. A lista não precisa dele, e ele carrega o token do webhook dentro."""
    credenciais: dict[str, Any]
    modelo_conversa: str
    modelo_fallback: str | None
    modelo_auxiliar: str
    modelo_visao: str
    modelo_transcricao: str
    buffer_segundos: int
    max_mensagens_por_resposta: int
    digitacao_caracteres_por_segundo: int
    digitacao_maximo_segundos: int
    ferramentas: list[str]
    emojis: str
    contatos_permitidos: list[str]
    handoff_destino: dict[str, Any] | None
    retomada_automatica_horas: int | None
    perfil: dict[str, Any]
    assina_nome: bool


def _saida(agente: Agente, empresa: str, com_webhook: bool = False) -> AgenteDoPainel:
    return AgenteDoPainel(
        id=agente.id,
        cliente_id=agente.cliente_id,
        empresa=empresa,
        nome=agente.nome,
        slug=agente.slug,
        canal=agente.canal,
        ativo=agente.ativo,
        criado_em=agente.criado_em.isoformat(),
        url_webhook=agentes_servico.url_webhook(agente) if com_webhook else None,
        credenciais=credenciais_visiveis(
            obter_canal(agente.canal), agentes_servico.credenciais(agente)
        ),
        modelo_conversa=agente.modelo_conversa,
        modelo_fallback=agente.modelo_fallback,
        modelo_auxiliar=agente.modelo_auxiliar,
        modelo_visao=agente.modelo_visao,
        modelo_transcricao=agente.modelo_transcricao,
        buffer_segundos=agente.buffer_segundos,
        max_mensagens_por_resposta=agente.max_mensagens_por_resposta,
        digitacao_caracteres_por_segundo=agente.digitacao_caracteres_por_segundo,
        digitacao_maximo_segundos=agente.digitacao_maximo_segundos,
        ferramentas=list(agente.ferramentas),
        emojis=agente.emojis,
        contatos_permitidos=list(agente.contatos_permitidos),
        handoff_destino=agente.handoff_destino,
        retomada_automatica_horas=agente.retomada_automatica_horas,
        perfil=dict(agente.perfil or {}),
        assina_nome=agente.assina_nome,
    )


async def _acha(s: AsyncSession, agente_id: uuid.UUID) -> tuple[Agente, str]:
    agente = await repo.agente(s, agente_id)
    if agente is None:
        raise HTTPException(status_code=404, detail="agente não encontrado")
    cliente = await clientes_repo.obter(s, agente.cliente_id)
    return agente, cliente.nome if cliente else ""


def _erro_de_negocio(erro: Exception) -> HTTPException:
    """O 428 é o do menu: falta o acesso do operador ao canal, e quem chamou repete com ele."""
    if isinstance(erro, AcessoNecessario):
        return HTTPException(status_code=428, detail=str(erro))
    if isinstance(erro, agentes_servico.NaoEncontrado):
        return HTTPException(status_code=404, detail=str(erro))
    if isinstance(erro, agentes_servico.Conflito):
        return HTTPException(status_code=409, detail=str(erro))
    return HTTPException(status_code=422, detail=str(erro))


DE_NEGOCIO = (
    AcessoNecessario,
    agentes_servico.NaoEncontrado,
    agentes_servico.Conflito,
    agentes_servico.CampoInvalido,
    CredencialInvalida,
    DestinoInvalido,
    ModeloInvalido,
)


# Empresas


class NovaEmpresa(BaseModel):
    nome: str = Field(min_length=1, max_length=200)


@router.post("/empresas", status_code=201)
async def cria_empresa(dados: NovaEmpresa, s: AsyncSession = Depends(sessao)) -> dict[str, Any]:
    """Primeiro passo do onboarding quando a empresa ainda não existe."""
    try:
        cliente = await clientes_servico.criar_cliente(s, dados.nome)
    except clientes_servico.ClienteJaExiste as erro:
        raise HTTPException(status_code=409, detail=str(erro)) from erro
    except ValueError as erro:
        raise HTTPException(status_code=422, detail=str(erro)) from erro
    return {"id": str(cliente.id), "nome": cliente.nome, "slug": cliente.slug, "ativo": cliente.ativo}


# Agentes


@router.get("/agentes")
async def lista(
    cliente_id: uuid.UUID | None = Query(default=None),
    ativo: bool | None = Query(default=None),
    s: AsyncSession = Depends(sessao),
) -> list[AgenteDoPainel]:
    if cliente_id is not None and await clientes_repo.obter(s, cliente_id) is None:
        raise HTTPException(status_code=404, detail="empresa não encontrada")
    return [_saida(a, empresa) for a, empresa in await repo.agentes(s, cliente_id, ativo)]


class NovoAgenteDoPainel(BaseModel):
    """O que o onboarding junta em sete passos e manda de uma vez só, no fim.

    Passo nenhum grava pela metade: ou o agente nasce inteiro, ou não nasce.
    """

    nome: str = Field(min_length=1, max_length=200)
    canal: str
    conexao: dict[str, Any] = Field(default_factory=dict)
    handoff_destino: dict[str, Any] | None = None
    retomada_automatica_horas: int | None = Field(default=None, ge=1, le=720)
    buffer_segundos: int = Field(default=8, ge=1, le=60)
    max_mensagens_por_resposta: int = Field(default=3, ge=1, le=10)
    digitacao_caracteres_por_segundo: int = Field(default=6, ge=1, le=30)
    digitacao_maximo_segundos: int = Field(default=20, ge=1, le=30)
    ferramentas: list[str] | None = None
    emojis: Literal["nenhum", "pouco", "medio", "muito"] = "nenhum"
    contatos_permitidos: list[str] | None = None
    modelo_conversa: str | None = Field(default=None, max_length=200)
    """Só a resposta é escolhida no onboarding. Resumo, visão e áudio nascem no mesmo provedor e
    mudam depois, na ficha."""


@router.post("/empresas/{cliente_id}/agentes", status_code=201)
async def cria(
    cliente_id: uuid.UUID, dados: NovoAgenteDoPainel, s: AsyncSession = Depends(sessao)
) -> AgenteDoPainel:
    cliente = await clientes_repo.obter(s, cliente_id)
    if cliente is None:
        raise HTTPException(status_code=404, detail="empresa não encontrada")
    if dados.canal not in CANAIS:
        raise HTTPException(status_code=422, detail=f"canal não suportado: {dados.canal}")
    try:
        agente, _ = await agentes_servico.criar_agente(
            s,
            cliente_id,
            nome=dados.nome,
            canal=dados.canal,
            conexao=dados.conexao,
            modelos={"modelo_conversa": dados.modelo_conversa},
            handoff_destino=dados.handoff_destino,
            buffer_segundos=dados.buffer_segundos,
            max_mensagens_por_resposta=dados.max_mensagens_por_resposta,
            retomada_automatica_horas=dados.retomada_automatica_horas,
            digitacao_caracteres_por_segundo=dados.digitacao_caracteres_por_segundo,
            digitacao_maximo_segundos=dados.digitacao_maximo_segundos,
            ferramentas=dados.ferramentas,
            emojis=dados.emojis,
            contatos_permitidos=dados.contatos_permitidos,
        )
    except DE_NEGOCIO as erro:
        raise _erro_de_negocio(erro) from erro
    return _saida(agente, cliente.nome, com_webhook=True)


@router.get("/agentes/{agente_id}")
async def ficha(agente_id: uuid.UUID, s: AsyncSession = Depends(sessao)) -> AgenteDoPainel:
    agente, empresa = await _acha(s, agente_id)
    return _saida(agente, empresa, com_webhook=True)


class EdicaoDoPainel(BaseModel):
    """Só o que veio muda. Cada seção do popup manda a sua parte, não a ficha inteira."""

    model_config = ConfigDict(extra="forbid")

    nome: str | None = Field(default=None, min_length=1, max_length=200)
    ativo: bool | None = None
    handoff_destino: dict[str, Any] | None = None
    buffer_segundos: int | None = Field(default=None, ge=1, le=60)
    max_mensagens_por_resposta: int | None = Field(default=None, ge=1, le=10)
    retomada_automatica_horas: int | None = Field(default=None, ge=1, le=720)
    digitacao_caracteres_por_segundo: int | None = Field(default=None, ge=1, le=30)
    digitacao_maximo_segundos: int | None = Field(default=None, ge=1, le=30)
    ferramentas: list[str] | None = None
    emojis: Literal["livre", "nenhum", "pouco", "medio", "muito"] | None = None
    contatos_permitidos: list[str] | None = None
    modelo_conversa: str | None = None
    modelo_fallback: str | None = None
    modelo_auxiliar: str | None = None
    modelo_visao: str | None = None
    modelo_transcricao: str | None = None


@router.patch("/agentes/{agente_id}")
async def edita(
    agente_id: uuid.UUID, dados: EdicaoDoPainel, s: AsyncSession = Depends(sessao)
) -> AgenteDoPainel:
    agente, empresa = await _acha(s, agente_id)
    mudancas = dados.model_dump(exclude_unset=True)
    # `ativo` não passa pelo serviço de edição: ele é o liga e desliga do agente, e o serviço cuida
    # de nome, modelos, ferramentas e destino.
    ativo = mudancas.pop("ativo", None)
    if mudancas:
        try:
            agente = await agentes_servico.editar_agente(
                s, agente.cliente_id, agente_id, mudancas, None, True
            )
        except DE_NEGOCIO as erro:
            raise _erro_de_negocio(erro) from erro
    if ativo is not None and ativo != agente.ativo:
        agente.ativo = ativo
        await s.commit()
        await s.refresh(agente)
    return _saida(agente, empresa, com_webhook=True)


class RemocaoDoPainel(BaseModel):
    confirmacao: str = Field(min_length=1, max_length=200, description="O nome do agente, digitado.")
    desconectar_canal: bool = True


@router.delete("/agentes/{agente_id}")
async def remove(
    agente_id: uuid.UUID, dados: RemocaoDoPainel, s: AsyncSession = Depends(sessao)
) -> dict[str, bool]:
    agente, _ = await _acha(s, agente_id)
    try:
        desconectado = await agentes_servico.remover_agente(
            s, agente.cliente_id, agente_id, dados.confirmacao, None, dados.desconectar_canal
        )
    except DE_NEGOCIO as erro:
        raise _erro_de_negocio(erro) from erro
    return {"removido": True, "canal_desconectado": desconectado}


# Catálogos


@router.get("/ferramentas")
async def catalogo() -> list[dict[str, Any]]:
    """As ferramentas que o agente pode usar, com a instrução de quando cada uma serve."""
    return [
        {"nome": f.nome, "rotulo": f.rotulo, "descricao": f.descricao, "padrao": f.padrao}
        for f in ferramentas.CATALOGO.values()
    ]


class ChaveDoProvedor(BaseModel):
    chave: str = Field(min_length=1, max_length=500)


@router.get("/modelos")
async def modelos(s: AsyncSession = Depends(sessao)) -> dict[str, Any]:
    """Provedores por função e quais já têm chave nesta instalação.

    A chave nunca volta para o navegador: o front só sabe se o provedor tem uma.
    """
    cfg = config()
    return {
        "provedores": list(PROVEDORES),
        "provedores_transcricao": list(PROVEDORES_TRANSCRICAO),
        "com_chave": await chaves.provedores_com_chave(s),
        "funcoes": [
            {"campo": "modelo_conversa", "funcao": "conversa", "rotulo": "Conversa", "obrigatorio": True},
            {"campo": "modelo_fallback", "funcao": "conversa", "rotulo": "Reserva", "obrigatorio": False},
            {"campo": "modelo_auxiliar", "funcao": "auxiliar", "rotulo": "Resumo do handoff", "obrigatorio": True},
            {"campo": "modelo_visao", "funcao": "visao", "rotulo": "Imagem e PDF", "obrigatorio": True},
            {"campo": "modelo_transcricao", "funcao": "transcricao", "rotulo": "Áudio", "obrigatorio": True},
        ],
        "padroes": {
            "modelo_conversa": cfg.modelo_conversa,
            "modelo_fallback": cfg.modelo_fallback,
            "modelo_visao": cfg.modelo_visao,
            "modelo_transcricao": cfg.modelo_transcricao,
        },
    }


@router.get("/modelos/{provedor}")
async def modelos_do_provedor(
    provedor: str, funcao: str = "conversa", s: AsyncSession = Depends(sessao)
) -> list[str]:
    """O que o provedor oferece para a função, com as sugestões primeiro."""
    try:
        return await chaves.listar_modelos(s, provedor, funcao)
    except ModeloInvalido as erro:
        raise HTTPException(status_code=422, detail=str(erro)) from erro


@router.put("/chaves/{provedor}", status_code=204)
async def guarda_chave(provedor: str, dados: ChaveDoProvedor, s: AsyncSession = Depends(sessao)) -> None:
    """Testa a chave no provedor e guarda cifrada. Vale para todo agente da instalação."""
    try:
        await chaves.guardar(s, provedor, dados.chave)
    except (chaves.ChaveRecusada, ModeloInvalido) as erro:
        raise HTTPException(status_code=422, detail=str(erro)) from erro


@router.get("/canais")
async def canais() -> list[dict[str, Any]]:
    """Os canais que esta instalação sabe conectar, na ordem em que o onboarding os oferece.

    Só a verdade do registro: o nome e se o canal é externo. O texto de cada cartão (o que ele
    serve e o que exige antes de começar) é do front, porque é copy de tela.
    """
    return [{"nome": nome, "externo": canal.externo} for nome, canal in CANAIS.items()]


# Trabalho: o perfil que escreve o prompt


class PerfilDoAgente(BaseModel):
    """O que a aba Trabalho pergunta. Tudo opcional: dá para responder aos poucos."""

    model_config = ConfigDict(extra="forbid")

    funcao: Literal["suporte", "vendas", "atendimento"] | None = None
    publico: str | None = Field(default=None, max_length=500)
    site: str | None = Field(default=None, max_length=300)
    sobre_empresa: str | None = Field(default=None, max_length=4000)
    assina_nome: bool | None = None


class PromptDoAgente(BaseModel):
    texto: str = Field(max_length=20000)


@router.get("/agentes/{agente_id}/prompt")
async def prompt(agente_id: uuid.UUID, s: AsyncSession = Depends(sessao)) -> dict[str, Any]:
    """O `persona.md` que o modelo recebe hoje, e o que o formulário escreveria no lugar dele."""
    agente, empresa = await _acha(s, agente_id)
    return {
        "texto": agentes_servico.le_prompt_do_agente(agente),
        "gerado": agentes_servico.monta_persona(agente, empresa),
        "arquivo": agente.arquivo_prompt,
        "perfil": dict(agente.perfil or {}),
    }


@router.put("/agentes/{agente_id}/prompt")
async def grava_prompt(
    agente_id: uuid.UUID, dados: PromptDoAgente, s: AsyncSession = Depends(sessao)
) -> dict[str, Any]:
    """Grava o prompt à mão. Salvar a aba Trabalho depois reescreve isto, e a tela avisa antes."""
    agente, _ = await _acha(s, agente_id)
    agentes_servico.escreve_prompt_do_agente(agente, dados.texto)
    return {"texto": agentes_servico.le_prompt_do_agente(agente)}


@router.put("/agentes/{agente_id}/perfil")
async def perfil(
    agente_id: uuid.UUID, dados: PerfilDoAgente, s: AsyncSession = Depends(sessao)
) -> dict[str, Any]:
    """Guarda as respostas da aba Trabalho e reescreve o `persona.md` a partir delas."""
    agente, empresa = await _acha(s, agente_id)
    campos = dados.model_dump(exclude_unset=True)
    assina = campos.pop("assina_nome", None)
    try:
        agente, texto = await agentes_servico.grava_perfil(
            s, agente.cliente_id, agente_id, campos, assina
        )
    except DE_NEGOCIO as erro:
        raise _erro_de_negocio(erro) from erro
    return {"agente": _saida(agente, empresa, com_webhook=True).model_dump(mode="json"), "prompt": texto}


# Canais


@router.get("/canais/situacao")
async def situacao_dos_canais(
    cliente_id: uuid.UUID | None = Query(default=None), s: AsyncSession = Depends(sessao)
) -> list[dict[str, Any]]:
    """Um por agente: quem é, por onde atende e se o canal respondeu agora.

    Cada canal é perguntado em separado, e o que não responder vira uma linha vermelha em vez de
    derrubar a tela: um canal fora do ar não pode esconder os outros.
    """
    if cliente_id is not None and await clientes_repo.obter(s, cliente_id) is None:
        raise HTTPException(status_code=404, detail="empresa não encontrada")
    linhas = []
    for agente, empresa in await repo.agentes(s, cliente_id, ativo=None):
        linhas.append(
            {
                "agente_id": str(agente.id),
                "agente": agente.nome,
                "empresa": empresa,
                "canal": agente.canal,
                "ativo": agente.ativo,
                "situacao": await canais_do_painel.situacao(agente),
            }
        )
    return linhas


class AcaoNoCanal(BaseModel):
    acao: Literal["reiniciar", "qr"]


@router.post("/agentes/{agente_id}/canal/acao")
async def acao_no_canal(
    agente_id: uuid.UUID, dados: AcaoNoCanal, s: AsyncSession = Depends(sessao)
) -> dict[str, Any]:
    """Reiniciar a sessão ou pedir o QR code. Só o WhatsApp pelo aparelho tem as duas."""
    agente, _ = await _acha(s, agente_id)
    if agente.canal != "waha":
        raise HTTPException(status_code=422, detail="este canal não tem essa ação")
    try:
        if dados.acao == "reiniciar":
            return {"situacao": await canais_do_painel.reinicia(agente)}
        return {"qr": await canais_do_painel.qr_code(agente)}
    except CredencialInvalida as erro:
        raise HTTPException(status_code=502, detail=str(erro)) from erro


# Conversa de teste
#
# O mesmo canal nativo que o `asimov conversar` usa no terminal. O agente responde de verdade, com o
# modelo e o prompt dele, e o turno entra no consumo como qualquer outro: é teste, não simulação.


class MensagemDeTeste(BaseModel):
    texto: str = Field(min_length=1, max_length=4000)
    conversa: str | None = Field(default=None, min_length=1, max_length=200)


@router.post("/agentes/{agente_id}/teste")
async def teste(
    agente_id: uuid.UUID,
    dados: MensagemDeTeste,
    request: Request,
    s: AsyncSession = Depends(sessao),
) -> dict[str, Any]:
    """Manda uma mensagem ao agente pela conversa de teste e devolve onde acompanhar a resposta."""
    agente, _ = await _acha(s, agente_id)
    try:
        enviada = await nativo_servico.enviar(
            s, request.app.state.fila, agente.cliente_id, agente_id, dados.texto.strip(), dados.conversa
        )
    except nativo_servico.NaoEncontrado as erro:
        raise HTTPException(status_code=404, detail=str(erro)) from erro
    return {
        "conversa": enviada.conversa,
        "conversa_id": str(enviada.conversa_id),
        "agendada": enviada.agendada,
    }


@router.get("/agentes/{agente_id}/teste/{conversa}")
async def le_teste(
    agente_id: uuid.UUID,
    conversa: str,
    depois: int = Query(default=0, ge=0),
    s: AsyncSession = Depends(sessao),
) -> dict[str, Any]:
    """O que o agente respondeu desde a última leitura, mais o digitando e o turno."""
    agente, _ = await _acha(s, agente_id)
    try:
        leitura = await nativo_servico.ler(s, agente.cliente_id, agente_id, conversa, depois)
    except nativo_servico.NaoEncontrado as erro:
        raise HTTPException(status_code=404, detail=str(erro)) from erro
    return {
        "mensagens": leitura.mensagens,
        "proxima": leitura.proxima,
        "digitando": leitura.digitando,
        "respondendo": leitura.respondendo,
        "turno": leitura.turno,
        "handoff": leitura.handoff,
    }
