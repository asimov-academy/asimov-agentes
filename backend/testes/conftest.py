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
os.environ["DIRETORIO_MODELOS"] = os.environ.get("TESTE_DIRETORIO_MODELOS", str(RAIZ / "modelos"))
os.environ["LOG_NIVEL"] = "DEBUG"

import httpx  # noqa: E402
import pytest  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app.canais import registro  # noqa: E402
from app.canais.base import Anexo, ArquivoBaixado, ArquivoGrandeDemais  # noqa: E402
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
        self.transferir_quebra = False

    async def conectar(self, dados: dict[str, Any], url_webhook: str, nome_agente: str) -> dict[str, Any]:
        return {
            "url": dados["url"],
            "account_id": dados["account_id"],
            "inbox_ids": dados["inbox_ids"],
            "api_access_token": TOKEN_BOT,
            "bot_id": BOT_ID,
            "bot_secret": BOT_SECRET,
        }

    async def desconectar(self, dados: dict[str, Any], credenciais: dict[str, Any]) -> None:
        self.desconectados.append(credenciais["bot_id"])

    async def agente_pode_falar(self, credenciais: dict[str, Any], conversa_externa: str) -> bool:
        return self.status == "pending"

    async def digitando(self, credenciais: dict[str, Any], conversa_externa: str, ligado: bool) -> None:
        self.digitando_chamadas.append(ligado)

    async def enviar_texto(self, credenciais: dict[str, Any], conversa_externa: str, texto: str) -> str:
        self.enviadas.append((conversa_externa, texto))
        return str(900000 + len(self.enviadas))

    async def transferir(self, credenciais: dict[str, Any], conversa_externa: str, destino: dict[str, Any] | None, nota: str) -> list[str]:
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
        self.chaves: dict[str, str] = {}
        self.falhar = falhar

    async def set(self, chave: str, valor: str, ex: int | None = None) -> None:
        if self.falhar:
            raise ConnectionError("redis fora do ar")
        self.chaves[chave] = valor

    async def enqueue_job(self, nome: str, *args: Any, **kwargs: Any) -> None:
        self.jobs.append((nome, *args))


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
