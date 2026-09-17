from typing import Any

from app.canais.base import Canal
from app.canais.chatwoot.canal import Chatwoot
from app.canais.nativo.canal import Nativo
from app.canais.waha.canal import Waha

CANAIS: dict[str, Canal] = {"chatwoot": Chatwoot(), "nativo": Nativo(), "waha": Waha()}


def obter_canal(nome: str) -> Canal:
    try:
        return CANAIS[nome]
    except KeyError as erro:
        raise KeyError(f"canal não suportado: {nome}") from erro


def credenciais_visiveis(canal: Canal, credenciais: dict[str, Any]) -> dict[str, Any]:
    """O que pode sair da API: campos secretos viram máscara."""
    from app.plataforma.cripto import mascara

    return {
        chave: mascara(str(valor)) if chave in canal.campos_secretos else valor
        for chave, valor in credenciais.items()
    }
