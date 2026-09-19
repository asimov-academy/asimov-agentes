"""Testes com Postgres e Redis reais.

Localmente: `TESTE_DATABASE_URL` e `TESTE_REDIS_URL` apontam para serviços da máquina.
No servidor, `deploy/publicar.sh` roda estes testes dentro do Compose com os serviços dele.
"""

import json
import os
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any

from cryptography.fernet import Fernet

RAIZ = Path(__file__).resolve().parents[2]

os.environ["DATABASE_URL"] = os.environ.get(
    "TESTE_DATABASE_URL", "postgresql+asyncpg:///asimov_teste?host=/tmp"
)
os.environ["REDIS_URL"] = os.environ.get("TESTE_REDIS_URL", "redis://localhost:6390/15")
os.environ["SUBDOMINIO_BOT"] = "bot.teste.local"
os.environ["CHAVE_API_ADMIN"] = "chave-admin-de-teste"
os.environ["CHAVE_CRIPTOGRAFIA"] = Fernet.generate_key().decode()
os.environ["MODELO_CONVERSA"] = "openai:gpt-5.5"
os.environ["MODELO_FALLBACK"] = "groq:llama-3.3-70b-versatile"
os.environ["MODELO_VISAO"] = "openai:gpt-5-mini"
os.environ["MODELO_TRANSCRICAO"] = "groq:whisper-large-v3-turbo"
os.environ["OPENAI_API_KEY"] = "sk-teste"
os.environ["GROQ_API_KEY"] = "gsk-teste"
os.environ["ANTHROPIC_API_KEY"] = ""
os.environ["GEMINI_API_KEY"] = ""
os.environ["DIRETORIO_PROMPTS"] = tempfile.mkdtemp(prefix="prompts-")
os.environ["DIRETORIO_MIDIA"] = tempfile.mkdtemp(prefix="midia-")
os.environ["DIRETORIO_CONHECIMENTO"] = tempfile.mkdtemp(prefix="conhecimento-")
os.environ["DIRETORIO_MODELOS"] = os.environ.get("TESTE_DIRETORIO_MODELOS", str(RAIZ / "modelos"))
os.environ["LOG_NIVEL"] = "DEBUG"
# O painel nasce desligado na instalação; nos testes ele sobe para as telas serem exercitadas.
os.environ["PAINEL_ATIVO"] = "1"
os.environ["SUBDOMINIO_APP"] = "app.teste.local"
# Front do painel: os testes não rodam `npm run build`, então usam uma cópia mínima com a mesma
# forma do que o Vite gera (um `index.html` e um arquivo em `assets/`).
_BASE_FRONT = Path(tempfile.mkdtemp(prefix="painel-"))
# Um arquivo fora da pasta do build, para o teste de travessia ter o que tentar roubar.
(_BASE_FRONT / "nao-deve-sair.txt").write_text("ISTO-NAO-PODE-SAIR")
_FRONT = _BASE_FRONT / "app"
(_FRONT / "assets").mkdir(parents=True)
(_FRONT / "index.html").write_text("<!doctype html><title>Painel</title><div id=raiz></div>")
(_FRONT / "assets" / "index-teste.js").write_text("console.log('painel')")
os.environ["DIRETORIO_PAINEL_APP"] = str(_FRONT)

def _confere_que_e_banco_de_teste() -> None:
    """As fixtures apagam tudo: apontar para o banco errado destruiria uma instalação de verdade.

    Um endereço sem `teste`/`test` no nome do banco, ou um Redis fora dos bancos altos, para aqui
    em vez de rodar (auditoria de 2026-09-18, A22).
    """
    # A query vem depois: `...///asimov_teste?host=/tmp` tem barra dentro do parâmetro.
    banco = os.environ["DATABASE_URL"].split("?", 1)[0].rsplit("/", 1)[-1]
    if "teste" not in banco and "test" not in banco:
        raise RuntimeError(
            f"DATABASE_URL aponta para o banco {banco!r}, que não parece de teste. "
            "Os testes apagam todas as tabelas: use TESTE_DATABASE_URL com um banco dedicado."
        )
    redis = os.environ["REDIS_URL"]
    indice = redis.split("?", 1)[0].rsplit("/", 1)[-1]
    if not (indice.isdigit() and int(indice) >= 10) and "teste" not in redis:
        raise RuntimeError(
            f"REDIS_URL aponta para {redis!r}. Os testes apagam chaves: use um índice alto "
            "(10 a 15) em TESTE_REDIS_URL."
        )


_confere_que_e_banco_de_teste()

import httpx  # noqa: E402
import pytest  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app.canais import registro  # noqa: E402
from app.canais.base import AcessoRecusado, Anexo, ArquivoBaixado, ArquivoGrandeDemais  # noqa: E402
from app.canais.chatwoot.assinatura import assina  # noqa: E402
from app.canais.chatwoot.canal import Chatwoot  # noqa: E402
from app.main import app  # noqa: E402
from app.modelos import Base  # noqa: E402
from app.plataforma.banco import fabrica_sessao, motor  # noqa: E402

ADMIN = {"X-Admin-Key": "chave-admin-de-teste"}
BOT_SECRET = "segredo-do-bot-xyz123"
TOKEN_BOT = "token-do-bot-abc987"
TOKEN_ADMIN = "token-do-administrador-qwe555"
BOT_ID = 42

# Acesso fictício do agente de exemplo (spec/dados.md).
CONEXAO_EXEMPLO = {
    "url": "https://chatwoot.exemplo.com.br",
    "token_admin": TOKEN_ADMIN,
    "account_id": 1,
    "inbox_ids": [3],
}


def e_resposta(info: Any) -> bool:
    """Chamada do turno de resposta (saída estruturada), e não resumo do handoff ou leitura de mídia (texto)."""
    return bool(info.output_tools) or info.model_request_parameters.output_mode == "native"


def resposta_falsa(info: Any, mensagens: list[str]) -> Any:
    """Resposta do modelo falso no formato que o agente pediu: nativo (texto JSON) ou pela tool de resposta."""
    from pydantic_ai.messages import ModelResponse, TextPart, ToolCallPart

    if info.output_tools:
        return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, {"mensagens": mensagens})])
    return ModelResponse(parts=[TextPart(json.dumps({"mensagens": mensagens}, ensure_ascii=False))])


class ChatwootFalso(Chatwoot):
    """Assinatura e interpretação reais; rede substituída por registro em memória."""

    def __init__(self) -> None:
        self.enviadas: list[tuple[str, str]] = []
        self.digitando_chamadas: list[bool] = []
        self.desconectados: list[int] = []
        self.status = "pending"
        self.arquivos: dict[str, ArquivoBaixado] = {}
        self.baixados: list[str] = []
        self.transferencias: list[tuple[str, dict[str, Any] | None, str]] = []
        self.contatos_avisados: list[str] = []
        self.transferir_quebra = False
        self.desconectar_recusa = False
        self.devolver_recusa = False
        self.devolvidas: list[str] = []
        self.assumidas: list[tuple[str, str | None]] = []
        self.renomeados: list[str] = []
        self.tokens_usados: list[str | None] = []

    def _confere_admin(self, dados: dict[str, Any]) -> None:
        self.tokens_usados.append(dados.get("token_admin"))
        if dados.get("token_admin") != TOKEN_ADMIN or self.desconectar_recusa:
            raise AcessoRecusado("o token precisa ser de um administrador da conta do Chatwoot")

    async def descobrir(self, dados: dict[str, Any]) -> dict[str, Any]:
        self._confere_admin(dados)
        return {"contas": [{"id": 1, "nome": "Loja Exemplo", "caixas": [{"id": 3, "nome": "WhatsApp"}], "atendentes": [], "times": []}]}

    async def conectar(self, dados: dict[str, Any], url_webhook: str, nome_agente: str) -> dict[str, Any]:
        self._confere_admin(dados)
        return {
            "url": dados["url"],
            "account_id": dados["account_id"],
            "inbox_ids": dados["inbox_ids"],
            "api_access_token": TOKEN_BOT,
            "bot_id": BOT_ID,
            "bot_secret": BOT_SECRET,
        }

    async def desconectar(self, dados: dict[str, Any], credenciais: dict[str, Any]) -> None:
        self._confere_admin(dados)
        self.desconectados.append(credenciais["bot_id"])

    async def renomear(self, dados: dict[str, Any], credenciais: dict[str, Any], nome: str) -> None:
        self._confere_admin(dados)
        self.renomeados.append(nome)

    async def devolver_ao_agente(self, credenciais: dict[str, Any], conversa_externa: str) -> None:
        if self.devolver_recusa:
            raise ConnectionError("chatwoot fora do ar")
        self.devolvidas.append(conversa_externa)
        self.status = "pending"

    async def assumir_no_canal(self, credenciais: dict[str, Any], conversa_externa: str, autor_externo: str | None) -> None:
        self.assumidas.append((conversa_externa, autor_externo))
        self.status = "open"

    async def agente_pode_falar(self, credenciais: dict[str, Any], conversa_externa: str, status: str) -> bool:
        return self.status == "pending"

    async def digitando(
        self,
        credenciais: dict[str, Any],
        conversa_externa: str,
        ligado: bool,
        ultima_mensagem: str | None = None,
    ) -> None:
        self.digitando_chamadas.append(ligado)

    async def enviar_texto(self, credenciais: dict[str, Any], conversa_externa: str, texto: str) -> str:
        self.enviadas.append((conversa_externa, texto))
        return str(900000 + len(self.enviadas))

    async def transferir(self, credenciais: dict[str, Any], conversa_externa: str, destino: dict[str, Any] | None, nota: str, codigo: str = "", contato: str = "") -> list[str]:
        self.contatos_avisados.append(contato)
        if self.transferir_quebra:
            raise ConnectionError("chatwoot fora do ar")
        self.transferencias.append((conversa_externa, destino, nota))
        self.status = "open"
        return []

    async def baixar_midia(self, credenciais: dict[str, Any], anexo: Anexo, limite_bytes: int) -> ArquivoBaixado:
        self.baixados.append(anexo.referencia)
        arquivo = self.arquivos[anexo.referencia]
        if len(arquivo.conteudo) > limite_bytes:
            raise ArquivoGrandeDemais("teste")
        return arquivo


class FilaFalsa:
    def __init__(self, falhar: bool = False) -> None:
        self.jobs: list[tuple[Any, ...]] = []
        self.adiamentos: list[int | None] = []
        self.chaves: dict[str, str] = {}
        self.falhar = falhar

    async def set(self, chave: str, valor: str, ex: int | None = None, nx: bool = False) -> bool | None:
        if self.falhar:
            raise ConnectionError("redis fora do ar")
        if nx and chave in self.chaves:
            return None
        self.chaves[chave] = valor
        return True

    async def get(self, chave: str) -> str | None:
        if self.falhar:
            raise ConnectionError("redis fora do ar")
        return self.chaves.get(chave)

    async def ping(self) -> bool:
        if self.falhar:
            raise ConnectionError("redis fora do ar")
        return True

    async def exists(self, chave: str) -> int:
        """O webhook consulta o lock da conversa antes de reagendar uma reentrega."""
        if self.falhar:
            raise ConnectionError("redis fora do ar")
        return int(chave in self.chaves)

    async def delete(self, chave: str) -> int:
        if self.falhar:
            raise ConnectionError("redis fora do ar")
        return int(self.chaves.pop(chave, None) is not None)

    async def enqueue_job(self, nome: str, *args: Any, **kwargs: Any) -> None:
        if self.falhar:
            raise ConnectionError("redis fora do ar")
        self.jobs.append((nome, *args))
        self.adiamentos.append(kwargs.get("_defer_by"))


@pytest.fixture(scope="session", autouse=True)
async def schema() -> None:
    async with motor().begin() as conexao:
        await conexao.run_sync(Base.metadata.drop_all)
        await conexao.run_sync(Base.metadata.create_all)


@pytest.fixture(autouse=True)
async def banco_limpo(schema: None) -> None:
    tabelas = ", ".join(t.name for t in reversed(Base.metadata.sorted_tables))
    async with motor().begin() as conexao:
        await conexao.execute(text(f"TRUNCATE {tabelas} CASCADE"))


@pytest.fixture
def canal() -> Any:
    falso = ChatwootFalso()
    original = registro.CANAIS["chatwoot"]
    registro.CANAIS["chatwoot"] = falso
    yield falso
    registro.CANAIS["chatwoot"] = original


@pytest.fixture
def fila() -> FilaFalsa:
    f = FilaFalsa()
    app.state.fila = f
    return f


@pytest.fixture
async def http() -> Any:
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://teste") as c:
        yield c


@pytest.fixture
def sessao() -> Any:
    return fabrica_sessao()


async def limpa_o_redis_do_painel() -> None:
    """Sessão, código e contador de erro vivem no Redis, que o `banco_limpo` não alcança."""
    from app.painel import servico as painel_servico

    async with painel_servico.conexao() as r:
        chaves = await r.keys("painel:*")
        if chaves:
            await r.delete(*chaves)


@pytest.fixture
async def painel(http: httpx.AsyncClient) -> Any:
    """Cliente próprio em https: o cookie da sessão é `Secure` e não viaja em http."""
    await limpa_o_redis_do_painel()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=http._transport.app),  # type: ignore[attr-defined]
        base_url="https://painel.teste",
    ) as c:
        yield c


async def cria_cliente_e_agente(http: httpx.AsyncClient, nome_cliente: str, nome_agente: str, **extra: Any) -> dict[str, Any]:
    cliente = (await http.post("/admin/clientes", json={"nome": nome_cliente}, headers=ADMIN)).json()
    resp = await http.post(
        f"/admin/clientes/{cliente['id']}/agentes",
        json={"nome": nome_agente, "canal": "chatwoot", "conexao": CONEXAO_EXEMPLO, **extra},
        headers=ADMIN,
    )
    assert resp.status_code == 201, resp.text
    agente = resp.json()
    agente["token"] = agente["url_webhook"].rsplit("/", 1)[1]
    return agente


def payload_chatwoot(
    mensagem_id: int = 1,
    conteudo: str = "oi",
    conversa: int = 1532,
    status: str = "pending",
    tipo: str = "incoming",
    remetente: dict[str, Any] | None = None,
    inbox: int = 3,
    anexos: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "attachments": anexos or [],
        "event": "message_created",
        "id": mensagem_id,
        "content": conteudo,
        "message_type": tipo,
        "private": False,
        "sender": remetente or {"id": 4812, "name": "Maria", "phone_number": "+5511999990000", "type": "contact"},
        "conversation": {"id": conversa, "status": status, "inbox_id": inbox},
        "inbox": {"id": inbox},
    }


async def envia_webhook(
    http: httpx.AsyncClient, token: str, payload: dict[str, Any], secret: str = BOT_SECRET, ts: str | None = None
) -> httpx.Response:
    corpo = json.dumps(payload).encode()
    ts = ts or str(int(time.time()))
    return await http.post(
        f"/webhook/chatwoot/{token}",
        content=corpo,
        headers={
            "Content-Type": "application/json",
            "X-Chatwoot-Timestamp": ts,
            "X-Chatwoot-Signature": assina(secret, corpo, ts),
            "X-Chatwoot-Delivery": str(uuid.uuid4()),
        },
    )
