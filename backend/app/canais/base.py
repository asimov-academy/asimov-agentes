"""Contrato que todo canal cumpre. Fora de `canais/`, ninguém sabe qual canal está atendendo."""

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Protocol


class CredencialInvalida(ValueError):
    """Mensagem em português, pronta para o setup mostrar ao operador."""


class Acao(StrEnum):
    IGNORAR = "ignorar"
    REGISTRAR = "registrar"
    """Grava na conversa, mas o agente não responde."""
    PROCESSAR = "processar"
    """Grava e agenda o buffer do turno."""


@dataclass(frozen=True)
class EntradaWebhook:
    corpo: bytes
    cabecalhos: Mapping[str, str]


@dataclass(frozen=True)
class Evento:
    acao: Acao
    motivo: str
    conversa_externa: str | None = None
    contato_externo: str | None = None
    contato_nome: str | None = None
    contato_telefone: str | None = None
    mensagem_externa: str | None = None
    texto: str | None = None
    autor: str = "contato"
    direcao: str = "entrada"
    tipo: str = "texto"


class Canal(Protocol):
    nome: str
    campos_secretos: frozenset[str]
    responde_200_em_assinatura_invalida: bool
    """True quando o canal pune resposta de erro (Chatwoot silencia o bot na conversa)."""

    async def testar(self, credenciais: dict[str, Any]) -> dict[str, Any]:
        """Confere as credenciais no próprio canal e devolve a versão normalizada."""
        ...

    def verificar(self, entrada: EntradaWebhook, credenciais: dict[str, Any]) -> bool: ...

    def interpretar(self, payload: dict[str, Any], credenciais: dict[str, Any]) -> Evento: ...

    async def agente_pode_falar(self, credenciais: dict[str, Any], conversa_externa: str) -> bool:
        """Relido na hora do turno: um humano pode ter assumido durante o buffer."""
        ...

    async def digitando(
        self, credenciais: dict[str, Any], conversa_externa: str, ligado: bool
    ) -> None: ...

    async def enviar_texto(
        self, credenciais: dict[str, Any], conversa_externa: str, texto: str
    ) -> str | None: ...
