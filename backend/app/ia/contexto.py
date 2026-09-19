from dataclasses import dataclass
from uuid import UUID


@dataclass
class ContextoTurno:
    """Estado que as tools do turno escrevem. O turno age sobre ele depois de enviar a resposta."""

    motivo_handoff: str | None = None
    cliente_id: UUID | None = None
    """De quem é a conversa. A busca na base filtra por ele, e sem ele a busca não acontece."""
    agente_id: UUID | None = None
    usou_base: bool = False
    """A resposta veio do material do cliente, e não da cabeça do modelo."""
