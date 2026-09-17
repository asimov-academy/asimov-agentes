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
    RETOMAR = "retomar"
    """O atendente devolveu a conversa ao agente: fecha o handoff aberto."""


class DestinoInvalido(ValueError):
    """Destino de handoff fora do formato do canal. Mensagem em português."""


class ArquivoGrandeDemais(ValueError):
    """O arquivo passou do limite durante o download."""


@dataclass(frozen=True)
class Anexo:
    """Arquivo que chegou com a mensagem, antes de ser baixado."""

    tipo: str
    """`audio`, `imagem`, `video` ou `documento`."""
    referencia: str
    """Como o canal acha o arquivo de novo (URL no Chatwoot, id da mídia na Meta)."""
    tipo_mime: str | None = None
    tamanho_bytes: int | None = None
    nome: str | None = None


@dataclass(frozen=True)
class ArquivoBaixado:
    conteudo: bytes
    tipo_mime: str


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
    anexos: tuple[Anexo, ...] = ()


class Canal(Protocol):
    nome: str
    campos_secretos: frozenset[str]
    responde_200_em_assinatura_invalida: bool
    """True quando o canal pune resposta de erro (Chatwoot silencia o bot na conversa)."""
    retoma_por_tempo: bool
    """True quando o agente volta sozinho depois de `retomada_automatica_horas` (canais diretos)."""

    async def descobrir(self, dados: dict[str, Any]) -> dict[str, Any]:
        """Com o acesso do operador, lista o que dá para conectar (contas, caixas, números)."""
        ...

    async def conectar(
        self, dados: dict[str, Any], url_webhook: str, nome_agente: str
    ) -> dict[str, Any]:
        """Configura o canal para chamar o webhook e devolve as credenciais de operação.

        O acesso do operador usado aqui nunca é guardado; só o que for devolvido.
        """
        ...

    async def desconectar(self, dados: dict[str, Any], credenciais: dict[str, Any]) -> None:
        """Desfaz `conectar`: na criação que não chegou a gravar e na remoção do agente.

        `dados` é o acesso do operador (no Chatwoot, só o token de administrador basta).
        Conexão que já não existe no canal não é erro; acesso recusado levanta CredencialInvalida.
        """
        ...

    async def renomear(self, dados: dict[str, Any], credenciais: dict[str, Any], nome: str) -> None:
        """Troca o nome com que o agente aparece no canal. `dados` é o acesso do operador."""
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

    def valida_destino_handoff(self, destino: dict[str, Any] | None) -> dict[str, Any] | None:
        """Normaliza o `handoff_destino` do agente ou levanta DestinoInvalido."""
        ...

    async def transferir(
        self,
        credenciais: dict[str, Any],
        conversa_externa: str,
        destino: dict[str, Any] | None,
        nota: str,
    ) -> list[str]:
        """Passa a conversa para humano: nota interna, atribuição ao destino e pausa do agente.

        Levanta se a pausa falhar. Devolve o que deu errado sem impedir a pausa (nota, atribuição).
        """
        ...

    async def devolver_ao_agente(self, credenciais: dict[str, Any], conversa_externa: str) -> None:
        """Operador retomou pelo menu: o canal volta a deixar o agente falar na conversa."""
        ...

    async def baixar_midia(
        self, credenciais: dict[str, Any], anexo: Anexo, limite_bytes: int
    ) -> ArquivoBaixado:
        """Baixa o anexo sem passar de `limite_bytes`; acima disso levanta ArquivoGrandeDemais."""
        ...
