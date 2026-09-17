"""Contrato que todo canal cumpre. Fora de `canais/`, ninguém sabe qual canal está atendendo."""

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Protocol


class CredencialInvalida(ValueError):
    """Mensagem em português, pronta para o setup mostrar ao operador."""


class AcessoRecusado(CredencialInvalida):
    """O canal recusou o acesso do operador (token errado, revogado ou sem ser administrador)."""


class Acao(StrEnum):
    IGNORAR = "ignorar"
    REGISTRAR = "registrar"
    """Grava na conversa, mas o agente não responde."""
    PROCESSAR = "processar"
    """Grava e agenda o buffer do turno."""
    PAUSAR = "pausar"
    """Grava e cala o agente: uma pessoa da empresa assumiu a conversa pelo próprio aparelho."""
    RETOMAR = "retomar"
    """O atendente devolveu a conversa ao agente: fecha o handoff aberto."""
    RETOMAR_POR_CODIGO = "retomar_por_codigo"
    """Nos canais diretos, quem recebeu o handoff mandou `/retomar <código>` na conversa dele."""


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
    codigo: str | None = None
    """Código do handoff em RETOMAR_POR_CODIGO: a conversa a retomar é achada por ele."""
    por: str | None = None
    """Quem devolveu a conversa ao agente, para o histórico do handoff. Vazio vale o canal."""
    autor_externo: str | None = None
    """Quem escreveu, no canal, quando não é o contato: o atendente que assumiu a conversa."""
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
    """True quando o agente pode voltar sozinho depois de `retomada_automatica_horas`."""
    pede_acesso_do_operador: bool
    """False quando criar, renomear e remover não precisam de token do operador (nativo)."""
    externo: bool
    """True quando o agente atende contatos de fora por este canal. Agente em canal que não é
    externo (nativo) pode ser conectado a um externo depois."""
    webhook_interno: bool
    """True quando o canal roda na própria VPS e chama a API pela rede do Compose (WAHA)."""

    def acesso_do_operador(self, dados: dict[str, Any]) -> dict[str, Any]:
        """Só a parte secreta do acesso do operador (no Chatwoot, o token de administrador), ou {}."""
        ...

    def endereco(self, dados: dict[str, Any]) -> str:
        """Onde o acesso do operador vale, a partir da conexão ou das credenciais do agente."""
        ...

    async def descobrir(self, dados: dict[str, Any]) -> dict[str, Any]:
        """Com o acesso do operador, lista o que dá para conectar (contas, caixas, números)."""
        ...

    async def conectar(
        self, dados: dict[str, Any], url_webhook: str, nome_agente: str
    ) -> dict[str, Any]:
        """Configura o canal para chamar o webhook e devolve as credenciais de operação.

        O acesso do operador não vai para as credenciais do agente; quem guarda é `acessos/`.
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

    def interpretar(
        self,
        payload: dict[str, Any],
        credenciais: dict[str, Any],
        destino: dict[str, Any] | None = None,
    ) -> Evento:
        """`destino` é o `handoff_destino` do agente: nos canais diretos, o número ou grupo de
        onde vem o `/retomar <código>`; nos outros, não muda nada."""
        ...

    async def agente_pode_falar(
        self, credenciais: dict[str, Any], conversa_externa: str, status: str
    ) -> bool:
        """Relido na hora do turno: um humano pode ter assumido durante o buffer.

        `status` é o da conversa aqui (`agente` ou `humano`). Canal que conduz pela própria
        ferramenta (Chatwoot) pergunta a ele; canal direto (WhatsApp), que não tem onde guardar,
        vale-se do status.
        """
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
        codigo: str = "",
    ) -> list[str]:
        """Passa a conversa para humano: nota interna, atribuição ao destino e pausa do agente.

        `codigo` é o do handoff, que os canais diretos mandam no aviso para o `/retomar`.
        Levanta se a pausa falhar. Devolve o que deu errado sem impedir a pausa (nota, atribuição).
        """
        ...

    def rotulo_da_conversa(self, conversa_externa: str) -> str:
        """Como a conversa aparece para uma pessoa (na WAHA, o número formatado)."""
        ...

    async def avisa_destino(
        self, credenciais: dict[str, Any], destino: dict[str, Any] | None, texto: str
    ) -> None:
        """Recado curto a quem recebeu o handoff (retomada por tempo). Canal sem isso não faz nada."""
        ...

    async def devolver_ao_agente(self, credenciais: dict[str, Any], conversa_externa: str) -> None:
        """O canal volta a deixar o agente falar na conversa: retomada pelo menu, por comando ou
        por tempo. No Chatwoot, conversa pendente e sem atendente atribuído."""
        ...

    async def assumir_no_canal(
        self, credenciais: dict[str, Any], conversa_externa: str, autor_externo: str | None
    ) -> None:
        """Uma pessoa da equipe assumiu a conversa: deixa isso à vista no canal.

        No Chatwoot, conversa aberta e atribuída a quem respondeu. Canal em que a conversa não tem
        dono (WhatsApp) não faz nada. Roda no worker, nunca dentro do webhook.
        """
        ...

    async def baixar_midia(
        self, credenciais: dict[str, Any], anexo: Anexo, limite_bytes: int
    ) -> ArquivoBaixado:
        """Baixa o anexo sem passar de `limite_bytes`; acima disso levanta ArquivoGrandeDemais."""
        ...
