"""Divisão da resposta em mensagens curtas, a pausa de ler e quanto tempo o agente fica "digitando".

O ritmo é a parte da humanização que não mora no modelo: buffer, pausa de leitura, velocidade de
digitação e teto são orquestração, e o modelo só decide o conteúdo (spec/fases.md, fase 10).
"""

import random
import re

DIGITANDO_MINIMO_SEGUNDOS = 1.0
VARIACAO = 0.15
"""Ninguém digita sempre no mesmo ritmo: cada mensagem varia até 15% para mais ou para menos."""

LEITURA_CARACTERES_POR_SEGUNDO = 45
"""Quem lê no celular lê rápido, mas lê: sem esta pausa o digitando começa no mesmo instante em que
a mensagem chega, que é o que mais denuncia robô."""

RITMOS: dict[str, dict[str, int]] = {
    "instantaneo": {
        "buffer_segundos": 2,
        "digitacao_caracteres_por_segundo": 30,
        "digitacao_maximo_segundos": 1,
        "leitura_maximo_segundos": 0,
    },
    "natural": {
        "buffer_segundos": 8,
        "digitacao_caracteres_por_segundo": 6,
        "digitacao_maximo_segundos": 20,
        "leitura_maximo_segundos": 4,
    },
    "reflexivo": {
        "buffer_segundos": 15,
        "digitacao_caracteres_por_segundo": 4,
        "digitacao_maximo_segundos": 25,
        "leitura_maximo_segundos": 8,
    },
}
"""Os três presets do painel e do menu. `manual` não está aqui: são os números que o operador
escolheu, e a pausa de leitura dele é a do `natural`."""

CAMPOS_DO_RITMO = ("buffer_segundos", "digitacao_caracteres_por_segundo", "digitacao_maximo_segundos")


def numeros_do_ritmo(ritmo: str) -> dict[str, int]:
    """O que escrever no agente quando o operador escolhe um preset. Vazio no `manual`."""
    preset = RITMOS.get(ritmo)
    return {campo: preset[campo] for campo in CAMPOS_DO_RITMO} if preset else {}


def ritmo_dos_numeros(numeros: dict[str, int]) -> str:
    """O nome do preset que bate com os três números, ou `manual` quando não bate com nenhum."""
    for nome, preset in RITMOS.items():
        if all(numeros.get(campo) == preset[campo] for campo in CAMPOS_DO_RITMO):
            return nome
    return "manual"


def pausa_de_leitura(
    texto_recebido: str, ritmo: str = "natural", sorteio: random.Random | None = None
) -> float:
    """Segundos entre a mensagem chegar e o digitando começar, como quem lê antes de responder."""
    teto = RITMOS.get(ritmo, RITMOS["natural"])["leitura_maximo_segundos"]
    if teto <= 0:
        return 0.0
    sorteio = sorteio or random.Random()
    lido = len(texto_recebido) / LEITURA_CARACTERES_POR_SEGUNDO
    return min(max(lido * sorteio.uniform(1 - VARIACAO, 1 + VARIACAO), 0.8), teto)


_CITACAO = re.compile(r"\(\s*\[([^\]]+)\]\((?:https?://[^)\s]+)\)\s*\)")
_LINK = re.compile(r"\[([^\]]+)\]\((?:https?://[^)\s]+)\)")
_RASTREIO = re.compile(r"[?&]utm_source=openai\b")
_NEGRITO = re.compile(r"\*\*(.+?)\*\*|__(.+?)__")
_TITULO = re.compile(r"^\s{0,3}#{1,6}\s+", re.MULTILINE)


def sem_markdown(texto: str) -> str:
    """Texto como chega no celular. A busca da OpenAI cita a fonte em markdown ("([site](link))"), que no
    WhatsApp aparece cru (Isa na VPS, v0.8.10): citação vira "(site)", link vira só o texto."""
    texto = _CITACAO.sub(r"(\1)", texto)
    texto = _LINK.sub(r"\1", texto)
    texto = _RASTREIO.sub("", texto)
    texto = _NEGRITO.sub(lambda m: m.group(1) or m.group(2), texto)
    texto = _TITULO.sub("", texto)
    return re.sub(r"[ \t]{2,}", " ", texto).strip()


def limita_mensagens(mensagens: list[str], maximo: int) -> list[str]:
    """Nunca passa do máximo do agente: o excedente é juntado na última mensagem. Sem markdown."""
    limpas = [sem_markdown(m) for m in mensagens if m and sem_markdown(m)]
    if len(limpas) <= maximo:
        return limpas
    return [*limpas[: maximo - 1], "\n\n".join(limpas[maximo - 1 :])]


def tempos_de_digitacao(
    textos: list[str],
    caracteres_por_segundo: int,
    maximo_segundos: int,
    ja_passou_segundos: float = 0.0,
    total_maximo_segundos: float = 90.0,
    sorteio: random.Random | None = None,
) -> list[float]:
    """Segundos de digitando antes de cada mensagem, como uma pessoa digitando no celular.

    Tempo = caracteres / velocidade, com variação, entre 1 s e o máximo do agente. O que o turno já
    levou (ler mídia, pensar a resposta) conta como digitação da primeira mensagem. A soma respeita
    `total_maximo_segundos`, que fica abaixo do lock da conversa.
    """
    sorteio = sorteio or random.Random()
    velocidade = max(caracteres_por_segundo, 1)
    tempos = [
        min(max(len(t) / velocidade * sorteio.uniform(1 - VARIACAO, 1 + VARIACAO), DIGITANDO_MINIMO_SEGUNDOS), maximo_segundos)
        for t in textos
    ]
    if tempos:
        tempos[0] = max(tempos[0] - ja_passou_segundos, DIGITANDO_MINIMO_SEGUNDOS)
    total = sum(tempos)
    if total > total_maximo_segundos:
        tempos = [t * total_maximo_segundos / total for t in tempos]
    return tempos
