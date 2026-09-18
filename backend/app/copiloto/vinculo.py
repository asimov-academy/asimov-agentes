"""O que o painel sabe da conta de IA do operador.

Tudo vem do `.env`, escrito por `asimov ia` (setup/lib/vinculo.sh). Nenhuma credencial passa por
aqui: o login fica onde o CLI oficial guarda, com a permissão dele, e só o contêiner do copiloto
enxerga essa pasta.
"""

from typing import Any

from app.plataforma.config import config

NOMES = {"claude_code": "Claude Code", "codex": "Codex"}
ASSINATURAS = {"claude_code": "Claude Pro ou Max", "codex": "ChatGPT Plus ou Pro"}
COMANDOS = {"claude_code": "claude", "codex": "codex"}


def cli() -> str:
    """claude_code ou codex. Instalação anterior ao vínculo não tem IA_CLI: vale o AGENTE_CODIGO."""
    cfg = config()
    escolhido = cfg.ia_cli or cfg.agente_codigo
    return escolhido if escolhido in NOMES else "claude_code"


def disponivel() -> bool:
    return config().ia_vinculada


def situacao() -> dict[str, Any]:
    """O cartão do copiloto no painel: ligado ou não, em que CLI e em que conta."""
    cfg = config()
    escolhido = cli()
    return {
        "vinculada": cfg.ia_vinculada,
        "cli": escolhido,
        "nome": NOMES[escolhido],
        "assinatura": ASSINATURAS[escolhido],
        "conta": cfg.ia_conta,
        # O login roda no terminal da VPS: o navegador não tem como abrir o fluxo do CLI.
        "comando": "asimov ia",
    }
