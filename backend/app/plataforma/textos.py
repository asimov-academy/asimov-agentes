import re
import unicodedata


def slug(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", sem_acento.lower()).strip("-") or "sem-nome"


def so_digitos(texto: str) -> str:
    return re.sub(r"\D", "", texto or "")


def mesmo_telefone(informado: str, do_canal: str) -> bool:
    """O operador digita o número de um jeito e o canal manda de outro (DDI, máscara, `@c.us`).

    Bate quando o mais curto é o fim do mais longo, com pelo menos 8 dígitos: `11988887777`
    encontra `5511988887777`, e dois números de DDDs diferentes continuam diferentes.
    """
    a, b = so_digitos(informado), so_digitos(do_canal)
    if len(a) < 8 or len(b) < 8:
        return False
    curto, longo = (a, b) if len(a) <= len(b) else (b, a)
    return longo.endswith(curto)
