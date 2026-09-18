import re
import unicodedata


def slug(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", sem_acento.lower()).strip("-") or "sem-nome"


def so_digitos(texto: str) -> str:
    return re.sub(r"\D", "", texto or "")


def variantes_do_telefone(digitos: str) -> set[str]:
    """No Brasil o mesmo celular circula com e sem o nono dígito, conforme a idade do cadastro."""
    variantes = {digitos}
    if len(digitos) == 13 and digitos.startswith("55") and digitos[4] == "9":
        variantes.add(digitos[:4] + digitos[5:])
    elif len(digitos) == 11 and digitos[2] == "9":
        variantes.add(digitos[:2] + digitos[3:])
    return variantes


def mesmo_telefone(informado: str, do_canal: str) -> bool:
    """O operador digita o número de um jeito e o canal manda de outro (DDI, máscara, nono dígito).

    Bate quando o mais curto é o fim do mais longo, com pelo menos 8 dígitos: `11988887777`
    encontra `5511988887777`, e dois números de DDDs diferentes continuam diferentes.
    """
    a, b = so_digitos(informado), so_digitos(do_canal)
    if len(a) < 8 or len(b) < 8:
        return False
    for um in variantes_do_telefone(a):
        for outro in variantes_do_telefone(b):
            curto, longo = (um, outro) if len(um) <= len(outro) else (outro, um)
            if longo.endswith(curto):
                return True
    return False


def telefone_legivel(digitos: str) -> str:
    """`5511988887777` vira `+55 11 98888-7777`. O que não for número volta como veio."""
    digitos = so_digitos(digitos)
    if not digitos:
        return ""
    if len(digitos) in (12, 13) and digitos.startswith("55"):
        ddd, resto = digitos[2:4], digitos[4:]
        return f"+55 {ddd} {resto[:-4]}-{resto[-4:]}"
    return f"+{digitos}"
