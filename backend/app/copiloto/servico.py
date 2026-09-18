"""Executa um turno do copiloto: monta o comando do CLI, roda e lê o que voltou.

Tudo o que é diferente entre Claude Code e Codex mora neste arquivo. O resto do módulo não sabe
qual CLI está instalado.

O que vale para os dois:

- **Modo não interativo.** Nada de TUI: um comando, um texto de entrada, uma resposta.
- **Sem ferramenta de código.** As únicas ferramentas liberadas são as do nosso servidor MCP
  (`app/copiloto/mcp.py`). O copiloto opera a plataforma, não a VPS.
- **A credencial nunca aparece aqui.** Ela está na pasta do CLI, montada no contêiner pelo
  Compose. Este arquivo não lê, não copia e não registra nada dela.
- **O fio da conversa é do CLI.** Ele guarda o histórico; nós guardamos só o identificador para
  retomar no turno seguinte.
"""

import asyncio
import json
import shutil
from typing import Any

import structlog

from app.copiloto import vinculo

log = structlog.get_logger()

FILA = "arq:fila:copiloto"
"""Fila própria do copiloto: o worker de atendimento não enxerga estes jobs, e vice-versa."""

TEMPO_LIMITE_SEGUNDOS = 420
"""Um turno com várias leituras demora. O job do worker tem folga sobre este teto."""
LIMITE_SAIDA_BYTES = 2 * 1024 * 1024

SISTEMA = """Você é o copiloto do painel da Asimov Academy. Você conversa com o operador, em
português do Brasil, e opera a plataforma de agentes de atendimento dele pelas ferramentas.

Responda curto, sem enfeite e sem repetir o que o operador acabou de dizer. Leia antes de propor.
Nunca invente id, nome de ferramenta ou modelo: pegue das ferramentas de listagem. Toda mudança
passa por uma proposta que o operador confirma; depois de propor, diga em uma frase o que propôs e
pare. Você não mexe em código, não roda comando na VPS e não conecta canal: isso é com o operador."""

# Ferramentas de código do Claude Code. Ficam de fora, uma a uma, porque `--allowedTools` sozinho
# não impede o que já vem ligado por padrão.
FERRAMENTAS_DE_CODIGO = (
    "Bash,Edit,Write,Read,Glob,Grep,Task,WebFetch,WebSearch,NotebookEdit,TodoWrite"
)
COMANDO_DO_MCP = ["-m", "app.copiloto.mcp"]


class CopilotoIndisponivel(RuntimeError):
    """Mensagem em português, pronta para a tela."""


def _python() -> str:
    return shutil.which("python") or "python3"


def mcp_json() -> str:
    """Configuração de MCP que o Claude Code lê, no formato dele."""
    return json.dumps(
        {"mcpServers": {"asimov": {"command": _python(), "args": COMANDO_DO_MCP}}}
    )


# Texto puro, sem ferramenta nenhuma: é o que o botão "Melhorar com IA" do onboarding precisa.
# Ele não lê a plataforma, não propõe nada e não mantém conversa; só devolve o texto reescrito.
def comando_de_texto(cli: str, pedido: str) -> list[str]:
    if cli == "codex":
        return ["codex", "exec", "--json", "--skip-git-repo-check", "--sandbox", "read-only", pedido]
    return [
        "claude", "-p", pedido,
        "--output-format", "json",
        # Sem servidor de MCP nenhum, nem o nosso: aqui o modelo só escreve.
        "--mcp-config", '{"mcpServers":{}}',
        "--strict-mcp-config",
        "--disallowedTools", FERRAMENTAS_DE_CODIGO,
    ]


def comando(cli: str, texto: str, conversa_cli: str = "") -> list[str]:
    """A linha de comando do turno. Um lugar só: é o primeiro ponto a conferir numa VPS."""
    if cli == "codex":
        # `resume` é subcomando de `exec` e vem antes das opções.
        linha = ["codex", "exec", *(["resume", "--last"] if conversa_cli else [])]
        linha += ["--json", "--skip-git-repo-check", "--sandbox", "read-only"]
        # O MCP entra pela linha de comando, não pelo config.toml: a pasta do Codex é do operador
        # e o setup não escreve nada lá dentro.
        linha += [
            "-c", f'mcp_servers.asimov.command="{_python()}"',
            "-c", 'mcp_servers.asimov.args=["-m","app.copiloto.mcp"]',
        ]
        # O Codex não tem prompt de sistema separado: ele vai junto do primeiro pedido, e o resto
        # da conversa já está no fio que o `resume` retoma.
        return [*linha, texto if conversa_cli else f"{SISTEMA}\n\n---\n\n{texto}"]

    linha = [
        "claude", "-p", texto,
        "--output-format", "json",
        "--mcp-config", mcp_json(),
        "--strict-mcp-config",
        "--allowedTools", "mcp__asimov",
        "--disallowedTools", FERRAMENTAS_DE_CODIGO,
        "--append-system-prompt", SISTEMA,
    ]
    if conversa_cli:
        linha += ["--resume", conversa_cli]
    return linha


# Quanto a rota do painel espera pelo worker antes de desistir. Curto de propósito: é um botão no
# meio do onboarding, e o operador não fica olhando para uma estrelinha girando por um minuto.
ESPERA_DO_TEXTO_SEGUNDOS = 75


async def melhora_texto(fila: Any, texto: str, empresa: str) -> str:
    """Chamada pela rota do painel: enfileira no worker do copiloto, que é quem tem o CLI, e espera.

    A API não executa o CLI: ela não tem o binário nem a credencial montada, e é o contêiner do
    copiloto que tem os dois.
    """
    job = await fila.enqueue_job("melhorar_texto", texto, empresa, _queue_name=FILA)
    return str(await job.result(timeout=ESPERA_DO_TEXTO_SEGUNDOS))


async def redige(pedido: str) -> str:
    """Um texto reescrito pela assinatura do operador, sem ferramenta nenhuma no caminho."""
    resposta, _ = await _roda(comando_de_texto(vinculo.cli(), pedido))
    return resposta


async def roda_turno(texto: str, conversa_cli: str = "") -> tuple[str, str]:
    """Devolve a resposta em texto e o identificador para retomar a conversa no próximo turno."""
    resposta, conversa = await _roda(comando(vinculo.cli(), texto, conversa_cli))
    return resposta, conversa or conversa_cli


async def _roda(linha: list[str]) -> tuple[str, str]:
    """Executa o CLI e lê o que voltou. Todo caminho de saída daqui é uma frase em português."""
    if not vinculo.disponivel():
        raise CopilotoIndisponivel(
            "nenhuma conta de IA vinculada nesta instalação; rode asimov ia no terminal da VPS"
        )
    cli = vinculo.cli()
    try:
        processo = await asyncio.create_subprocess_exec(
            *linha, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
    except FileNotFoundError as erro:
        raise CopilotoIndisponivel(
            f"{vinculo.NOMES[cli]} não está instalado neste contêiner"
        ) from erro

    try:
        saida, erro_bruto = await asyncio.wait_for(
            processo.communicate(), timeout=TEMPO_LIMITE_SEGUNDOS
        )
    except TimeoutError as erro:
        processo.kill()
        raise CopilotoIndisponivel(
            "o copiloto demorou demais para responder; tente de novo com um pedido menor"
        ) from erro

    # O stdout entra no log junto do stderr: o Claude Code sai com código 1 e stderr vazio quando
    # não enxerga a credencial, e sem isto todo erro do CLI virava "não conseguiu responder".
    detalhe = erro_bruto[:2000].decode("utf-8", "replace").strip()
    if processo.returncode != 0:
        contou = saida[:2000].decode("utf-8", "replace").strip()
        log.warning(
            "copiloto_falhou", cli=cli, codigo=processo.returncode, detalhe=detalhe, saida=contou
        )
        raise CopilotoIndisponivel(_motivo(f"{detalhe}\n{contou}"))
    resposta, conversa = (
        _le_codex(saida) if cli == "codex" else _le_claude(saida[:LIMITE_SAIDA_BYTES])
    )
    if not resposta:
        log.warning("copiloto_sem_resposta", cli=cli, detalhe=detalhe)
        raise CopilotoIndisponivel("o copiloto não respondeu desta vez; tente de novo")
    return resposta, conversa


def _motivo(detalhe: str) -> str:
    """O erro do CLI em uma frase que o operador entenda, sem jogar a saída crua na tela."""
    baixo = detalhe.lower()
    if (
        "login" in baixo
        or "auth" in baixo
        or "credential" in baixo
        or "401" in baixo
        or "sign in" in baixo
        or "logged in" in baixo
    ):
        return "a conta de IA não está mais conectada; rode asimov ia no terminal da VPS"
    if "rate" in baixo or "limit" in baixo or "quota" in baixo or "429" in baixo:
        return "a assinatura bateu no limite de uso da janela; tente de novo mais tarde"
    return "o copiloto não conseguiu responder desta vez"


def _le_claude(saida: bytes) -> tuple[str, str]:
    """`--output-format json` devolve um objeto só, com a resposta e a sessão para retomar."""
    try:
        dados: Any = json.loads(saida.decode("utf-8", "replace") or "{}")
    except json.JSONDecodeError:
        return saida.decode("utf-8", "replace").strip(), ""
    if isinstance(dados, list):
        dados = next((d for d in reversed(dados) if isinstance(d, dict)), {})
    if not isinstance(dados, dict):
        return "", ""
    return str(dados.get("result") or "").strip(), str(dados.get("session_id") or "")


def _le_codex(saida: bytes) -> tuple[str, str]:
    """`--json` devolve um evento por linha. Vale a última mensagem do agente."""
    resposta = ""
    conversa = ""
    for linha in saida.decode("utf-8", "replace").splitlines():
        linha = linha.strip()
        if not linha.startswith("{"):
            continue
        try:
            evento = json.loads(linha)
        except json.JSONDecodeError:
            continue
        conversa = _texto(evento, ("session_id", "conversation_id", "thread_id")) or conversa
        mensagem = _mensagem_do_codex(evento)
        if mensagem:
            resposta = mensagem
    return resposta.strip(), conversa


def _mensagem_do_codex(evento: dict[str, Any]) -> str:
    corpo = evento.get("msg") if isinstance(evento.get("msg"), dict) else evento
    item = corpo.get("item") if isinstance(corpo.get("item"), dict) else corpo
    tipo = str(item.get("type") or corpo.get("type") or "")
    if tipo not in ("agent_message", "assistant_message", "message"):
        return ""
    texto = item.get("message") or item.get("text") or ""
    if not texto and isinstance(item.get("content"), list):
        texto = "".join(
            p.get("text", "") for p in item["content"] if isinstance(p, dict)
        )
    return str(texto)


def _texto(evento: dict[str, Any], chaves: tuple[str, ...]) -> str:
    for chave in chaves:
        valor = evento.get(chave)
        if isinstance(valor, str) and valor:
            return valor
    return ""
