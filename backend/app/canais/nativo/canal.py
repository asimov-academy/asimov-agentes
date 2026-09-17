"""Canal nativo: o agente conversa com o operador no terminal, sem canal externo.

Não tem conexão, credenciais nem webhook. O terminal manda a mensagem pela rota administrativa
(`canais/nativo/rotas.py`), que grava e agenda o buffer como um webhook faria; o turno é o mesmo dos
outros canais. Envio e digitando ficam no Redis para o terminal ler (`memoria.py`).

Handoff: registra, o terminal mostra motivo, resumo e código, e o agente fica calado na conversa até
o operador retomar.
"""

import uuid
from typing import Any

from app.canais.base import Anexo, ArquivoBaixado, EntradaWebhook, Evento
from app.canais.nativo import memoria

ID_CONTATO = "terminal"


class Nativo:
    nome = "nativo"
    campos_secretos: frozenset[str] = frozenset()
    responde_200_em_assinatura_invalida = False
    retoma_por_tempo = False
    pede_acesso_do_operador = False
    externo = False
    webhook_interno = False

    def acesso_do_operador(self, dados: dict[str, Any]) -> dict[str, Any]:
        return {}

    def endereco(self, dados: dict[str, Any]) -> str:
        return ""

    async def descobrir(self, dados: dict[str, Any]) -> dict[str, Any]:
        return {}

    async def conectar(self, dados: dict[str, Any], url_webhook: str, nome_agente: str) -> dict[str, Any]:
        return {}

    async def desconectar(self, dados: dict[str, Any], credenciais: dict[str, Any]) -> None:
        return None

    async def renomear(self, dados: dict[str, Any], credenciais: dict[str, Any], nome: str) -> None:
        return None

    def verificar(self, entrada: EntradaWebhook, credenciais: dict[str, Any]) -> bool:
        """Sem webhook: qualquer chamada em /webhook/nativo é recusada."""
        return False

    def interpretar(
        self, payload: dict[str, Any], credenciais: dict[str, Any], destino: dict[str, Any] | None = None
    ) -> Evento:
        raise NotImplementedError("o canal nativo não recebe webhook")

    async def agente_pode_falar(
        self, credenciais: dict[str, Any], conversa_externa: str, status: str
    ) -> bool:
        return not await memoria.humano_conduz(conversa_externa)

    async def digitando(self, credenciais: dict[str, Any], conversa_externa: str, ligado: bool) -> None:
        await memoria.muda_digitando(conversa_externa, ligado)

    async def enviar_texto(self, credenciais: dict[str, Any], conversa_externa: str, texto: str) -> str:
        id_externo = uuid.uuid4().hex
        await memoria.guarda_saida(conversa_externa, {"id": id_externo, "texto": texto})
        return id_externo

    def valida_destino_handoff(self, destino: dict[str, Any] | None) -> dict[str, Any] | None:
        """No terminal, quem recebe o handoff é o próprio operador."""
        return None

    async def transferir(
        self,
        credenciais: dict[str, Any],
        conversa_externa: str,
        destino: dict[str, Any] | None,
        nota: str,
        codigo: str = "",
    ) -> list[str]:
        await memoria.muda_humano(conversa_externa, True)
        return []

    def rotulo_da_conversa(self, conversa_externa: str) -> str:
        return "a conversa do terminal"

    async def avisa_destino(
        self, credenciais: dict[str, Any], destino: dict[str, Any] | None, texto: str
    ) -> None:
        """Quem recebe o handoff no terminal é o próprio operador, que está vendo a conversa."""
        return None

    async def devolver_ao_agente(self, credenciais: dict[str, Any], conversa_externa: str) -> None:
        await memoria.muda_humano(conversa_externa, False)

    async def baixar_midia(self, credenciais: dict[str, Any], anexo: Anexo, limite_bytes: int) -> ArquivoBaixado:
        raise NotImplementedError("o terminal só manda texto")
