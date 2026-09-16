"""Divisão da resposta em mensagens curtas e tempo de digitação entre elas."""

MS_POR_CARACTERE = 28
DELAY_MINIMO_MS = 1000
DELAY_MAXIMO_MS = 4000


def limita_mensagens(mensagens: list[str], maximo: int) -> list[str]:
    """Nunca passa do máximo do agente: o excedente é juntado na última mensagem."""
    limpas = [m.strip() for m in mensagens if m and m.strip()]
    if len(limpas) <= maximo:
        return limpas
    return [*limpas[: maximo - 1], "\n\n".join(limpas[maximo - 1 :])]


def delay_ms(texto: str) -> int:
    return max(DELAY_MINIMO_MS, min(len(texto) * MS_POR_CARACTERE, DELAY_MAXIMO_MS))
