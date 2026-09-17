from dataclasses import dataclass


@dataclass
class ContextoTurno:
    """Estado que as tools do turno escrevem. O turno age sobre ele depois de enviar a resposta."""

    motivo_handoff: str | None = None
