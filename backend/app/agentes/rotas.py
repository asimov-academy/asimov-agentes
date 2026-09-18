import uuid
from datetime import datetime
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.acessos import servico as acessos_servico
from app.acessos.servico import AcessoNecessario
from app.agentes import repo, servico
from app.agentes.modelos import Agente
from app.canais.base import CredencialInvalida, DestinoInvalido
from app.canais.registro import CANAIS, credenciais_visiveis, obter_canal
from app.ia import ferramentas
from app.ia.provedores import ModeloInvalido
from app.plataforma.admin import exige_admin
from app.plataforma.banco import sessao

router = APIRouter(prefix="/admin", dependencies=[Depends(exige_admin)])


class Modelos(BaseModel):
    modelo_conversa: str | None = None
    modelo_fallback: str | None = None
    modelo_auxiliar: str | None = None
    modelo_visao: str | None = None
    modelo_transcricao: str | None = None


class NovoAgente(BaseModel):
    nome: str = Field(min_length=1, max_length=200)
    canal: str
    conexao: dict[str, Any] = Field(
        default_factory=dict,
        description="Acesso do operador ao canal (Chatwoot: url, conta, caixas e, se não houver guardado, token_admin; nativo: nada). O token que funcionar fica guardado cifrado.",
    )
    modelos: Modelos = Modelos()
    handoff_destino: dict[str, Any] | None = None
    buffer_segundos: int = Field(default=8, ge=1, le=60)
    max_mensagens_por_resposta: int = Field(default=3, ge=1, le=10)
    retomada_automatica_horas: int | None = Field(default=None, ge=1, le=720)
    digitacao_caracteres_por_segundo: int = Field(default=6, ge=1, le=30)
    digitacao_maximo_segundos: int = Field(default=20, ge=1, le=30)
    ferramentas: list[str] | None = Field(default=None, description="Padrão: nenhuma. O agente nasce cru.")
    emojis: Literal["nenhum", "pouco", "medio", "muito"] = Field(
        default="nenhum", description="Quanto o agente usa emoji. Padrão: nenhum, que é o agente cru."
    )
    tom: Literal["formal", "normal", "descontraido"] = Field(
        default="normal", description="Como o agente fala. Muda o jeito, nunca o conteúdo."
    )
    transfere_para_humano: bool = Field(
        default=True, description="Desligado, o agente nunca promete atendimento humano."
    )
    restringe_temas: bool = Field(
        default=True, description="Ligado (o padrão), o agente só fala do que é da empresa."
    )
    contatos_permitidos: list[str] | None = Field(
        default=None,
        description="Telefones que o agente atende. Vazio (o padrão) atende qualquer pessoa; com lista, o resto é ignorado.",
    )


class EdicaoAgente(BaseModel):
    """Só os campos enviados mudam. `null` esvazia o que pode ficar vazio (fallback, destino, retomada)."""

    model_config = ConfigDict(extra="forbid")

    nome: str | None = Field(default=None, min_length=1, max_length=200)
    handoff_destino: dict[str, Any] | None = None
    buffer_segundos: int | None = Field(default=None, ge=1, le=60)
    max_mensagens_por_resposta: int | None = Field(default=None, ge=1, le=10)
    retomada_automatica_horas: int | None = Field(default=None, ge=1, le=720)
    digitacao_caracteres_por_segundo: int | None = Field(default=None, ge=1, le=30)
    digitacao_maximo_segundos: int | None = Field(default=None, ge=1, le=30)
    ferramentas: list[str] | None = None
    emojis: Literal["livre", "nenhum", "pouco", "medio", "muito"] | None = None
    tom: Literal["formal", "normal", "descontraido"] | None = None
    transfere_para_humano: bool | None = None
    restringe_temas: bool | None = None
    contatos_permitidos: list[str] | None = None
    modelo_conversa: str | None = None
    modelo_fallback: str | None = None
    modelo_auxiliar: str | None = None
    modelo_visao: str | None = None
    modelo_transcricao: str | None = None
    conexao: dict[str, Any] | None = Field(
        default=None,
        description="Acesso do operador (Chatwoot: token_admin); sem ele, vale o guardado. Funcionando, fica guardado.",
    )
    renomear_no_canal: bool = Field(default=True, description="Leva o nome novo ao canal (nome do bot no Chatwoot).")


class NovaConexao(BaseModel):
    canal: str
    conexao: dict[str, Any] = Field(
        default_factory=dict,
        description="Acesso do operador ao canal, como na criação (Chatwoot: url, conta, caixas e token_admin se não houver guardado).",
    )
    handoff_destino: dict[str, Any] | None = None
    retomada_automatica_horas: int | None = Field(default=None, ge=1, le=720)


class Remocao(BaseModel):
    confirmacao: str = Field(min_length=1, max_length=200, description="Nome do agente.")
    conexao: dict[str, Any] | None = Field(
        default=None,
        description="Acesso do operador (Chatwoot: token_admin); sem ele, vale o guardado. Funcionando, fica guardado.",
    )
    desconectar_canal: bool = Field(
        default=True, description="Desfaz a conexão no canal (apaga o bot no Chatwoot). False só com o canal fora do ar."
    )


class RemocaoSaida(BaseModel):
    removido: bool
    canal_desconectado: bool


class AgenteSaida(BaseModel):
    id: uuid.UUID
    cliente_id: uuid.UUID
    nome: str
    slug: str
    canal: str
    url_webhook: str
    url_privacidade: str
    credenciais: dict[str, Any]
    arquivo_prompt: str
    modelo_conversa: str
    modelo_fallback: str | None
    modelo_auxiliar: str
    modelo_visao: str
    modelo_transcricao: str
    buffer_segundos: int
    max_mensagens_por_resposta: int
    handoff_destino: dict[str, Any] | None
    retomada_automatica_horas: int | None
    digitacao_caracteres_por_segundo: int
    digitacao_maximo_segundos: int
    ferramentas: list[str]
    emojis: str
    tom: str
    transfere_para_humano: bool
    restringe_temas: bool
    contatos_permitidos: list[str]
    ativo: bool


def _saida(agente: Agente) -> AgenteSaida:
    dados = {c: getattr(agente, c) for c in AgenteSaida.model_fields if hasattr(agente, c)}
    dados["url_webhook"] = servico.url_webhook(agente)
    dados["url_privacidade"] = servico.url_privacidade(agente)
    dados["credenciais"] = credenciais_visiveis(
        obter_canal(agente.canal), servico.credenciais(agente)
    )
    return AgenteSaida(**dados)


class Acesso(BaseModel):
    conexao: dict[str, Any]


def precisa_acesso(erro: AcessoNecessario) -> HTTPException:
    """428: o menu pede o token de administrador e repete a chamada com ele."""
    return HTTPException(status_code=428, detail=str(erro))


@router.post("/canais/{canal}/descobrir")
async def descobrir(canal: str, dados: Acesso, s: AsyncSession = Depends(sessao)) -> dict[str, Any]:
    """Lista o que o acesso do operador enxerga no canal. Grava só o acesso, se era novo."""
    if canal not in CANAIS:
        raise HTTPException(status_code=404, detail="canal não suportado")
    try:
        return await servico.descobrir(s, canal, dados.conexao)
    except AcessoNecessario as erro:
        raise precisa_acesso(erro) from erro
    except CredencialInvalida as erro:
        raise HTTPException(status_code=422, detail=str(erro)) from erro


@router.post("/clientes/{cliente_id}/agentes", status_code=201, response_model=AgenteSaida)
async def criar(
    cliente_id: uuid.UUID, dados: NovoAgente, s: AsyncSession = Depends(sessao)
) -> AgenteSaida:
    if dados.canal not in CANAIS:
        raise HTTPException(status_code=422, detail=f"canal não suportado: {dados.canal}")
    try:
        agente, _ = await servico.criar_agente(
            s,
            cliente_id,
            nome=dados.nome,
            canal=dados.canal,
            conexao=dados.conexao,
            modelos=dados.modelos.model_dump(exclude_none=True),
            handoff_destino=dados.handoff_destino,
            buffer_segundos=dados.buffer_segundos,
            max_mensagens_por_resposta=dados.max_mensagens_por_resposta,
            retomada_automatica_horas=dados.retomada_automatica_horas,
            digitacao_caracteres_por_segundo=dados.digitacao_caracteres_por_segundo,
            digitacao_maximo_segundos=dados.digitacao_maximo_segundos,
            ferramentas=dados.ferramentas,
            emojis=dados.emojis,
            tom=dados.tom,
            transfere_para_humano=dados.transfere_para_humano,
            restringe_temas=dados.restringe_temas,
            contatos_permitidos=dados.contatos_permitidos,
        )
    except servico.NaoEncontrado as erro:
        raise HTTPException(status_code=404, detail=str(erro)) from erro
    except servico.Conflito as erro:
        raise HTTPException(status_code=409, detail=str(erro)) from erro
    except AcessoNecessario as erro:
        raise precisa_acesso(erro) from erro
    except (CredencialInvalida, ModeloInvalido, DestinoInvalido, servico.CampoInvalido) as erro:
        raise HTTPException(status_code=422, detail=str(erro)) from erro
    return _saida(agente)


@router.get("/agentes", response_model=list[AgenteSaida])
async def listar(
    cliente_id: uuid.UUID | None = Query(default=None), s: AsyncSession = Depends(sessao)
) -> list[AgenteSaida]:
    agentes = (
        await repo.listar(s, cliente_id)
        if cliente_id
        else await repo.listar_de_todos_os_clientes(s)
    )
    return [_saida(a) for a in agentes]


@router.get("/clientes/{cliente_id}/agentes/{agente_id}", response_model=AgenteSaida)
async def ver(
    cliente_id: uuid.UUID, agente_id: uuid.UUID, s: AsyncSession = Depends(sessao)
) -> AgenteSaida:
    agente = await repo.obter(s, cliente_id, agente_id)
    if agente is None:
        raise HTTPException(status_code=404, detail="agente não encontrado")
    return _saida(agente)


@router.patch("/clientes/{cliente_id}/agentes/{agente_id}", response_model=AgenteSaida)
async def editar(
    cliente_id: uuid.UUID, agente_id: uuid.UUID, dados: EdicaoAgente, s: AsyncSession = Depends(sessao)
) -> AgenteSaida:
    try:
        agente = await servico.editar_agente(
            s,
            cliente_id,
            agente_id,
            dados.model_dump(exclude_unset=True, exclude={"conexao", "renomear_no_canal"}),
            dados.conexao,
            dados.renomear_no_canal,
        )
    except servico.NaoEncontrado as erro:
        raise HTTPException(status_code=404, detail=str(erro)) from erro
    except AcessoNecessario as erro:
        raise precisa_acesso(erro) from erro
    except (DestinoInvalido, ModeloInvalido, servico.CampoInvalido, CredencialInvalida) as erro:
        raise HTTPException(status_code=422, detail=str(erro)) from erro
    return _saida(agente)


@router.post("/clientes/{cliente_id}/agentes/{agente_id}/canal", response_model=AgenteSaida)
async def conectar(
    cliente_id: uuid.UUID, agente_id: uuid.UUID, dados: NovaConexao, s: AsyncSession = Depends(sessao)
) -> AgenteSaida:
    """Liga num canal externo um agente criado sem canal (nativo)."""
    if dados.canal not in CANAIS:
        raise HTTPException(status_code=422, detail=f"canal não suportado: {dados.canal}")
    try:
        agente = await servico.conectar_canal(
            s,
            cliente_id,
            agente_id,
            dados.canal,
            dados.conexao,
            dados.handoff_destino,
            dados.retomada_automatica_horas,
        )
    except servico.NaoEncontrado as erro:
        raise HTTPException(status_code=404, detail=str(erro)) from erro
    except servico.Conflito as erro:
        raise HTTPException(status_code=409, detail=str(erro)) from erro
    except AcessoNecessario as erro:
        raise precisa_acesso(erro) from erro
    except (CredencialInvalida, DestinoInvalido, servico.CampoInvalido) as erro:
        raise HTTPException(status_code=422, detail=str(erro)) from erro
    return _saida(agente)


@router.delete("/clientes/{cliente_id}/agentes/{agente_id}", response_model=RemocaoSaida)
async def remover(
    cliente_id: uuid.UUID, agente_id: uuid.UUID, dados: Remocao, s: AsyncSession = Depends(sessao)
) -> RemocaoSaida:
    try:
        desconectado = await servico.remover_agente(
            s, cliente_id, agente_id, dados.confirmacao, dados.conexao, dados.desconectar_canal
        )
    except servico.NaoEncontrado as erro:
        raise HTTPException(status_code=404, detail=str(erro)) from erro
    except AcessoNecessario as erro:
        raise precisa_acesso(erro) from erro
    except (CredencialInvalida, servico.CampoInvalido) as erro:
        raise HTTPException(status_code=422, detail=str(erro)) from erro
    return RemocaoSaida(removido=True, canal_desconectado=desconectado)


class AcessoGuardado(BaseModel):
    endereco: str
    atualizado_em: datetime


@router.get("/canais/{canal}/acessos", response_model=list[AcessoGuardado])
async def acessos(canal: str, s: AsyncSession = Depends(sessao)) -> list[AcessoGuardado]:
    """Onde há acesso do operador guardado. O token nunca sai."""
    return [AcessoGuardado(**a) for a in await acessos_servico.enderecos(s, canal)]


@router.delete("/canais/{canal}/acessos", status_code=204)
async def esquecer_acesso(
    canal: str, endereco: str = Query(min_length=1), s: AsyncSession = Depends(sessao)
) -> None:
    if not await acessos_servico.esquecer(s, canal, endereco.rstrip("/")):
        raise HTTPException(status_code=404, detail="nenhum acesso guardado nesse endereço")


class FerramentaSaida(BaseModel):
    nome: str
    rotulo: str
    descricao: str
    padrao: bool


@router.get("/ferramentas", response_model=list[FerramentaSaida])
async def listar_ferramentas() -> list[FerramentaSaida]:
    """Catálogo que o menu mostra para ligar e desligar por agente."""
    return [
        FerramentaSaida(nome=f.nome, rotulo=f.rotulo, descricao=f.descricao, padrao=f.padrao)
        for f in ferramentas.CATALOGO.values()
    ]
