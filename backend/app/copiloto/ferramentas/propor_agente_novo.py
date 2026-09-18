"""Proposta de agente novo, no canal nativo.

Só o canal nativo: ele é o único que não precisa de credencial de fora, então o copiloto consegue
criar sozinho. Conectar o agente ao Chatwoot ou ao WhatsApp continua no passo a passo do painel,
que é onde o operador cola token e lê QR code.
"""

import uuid

from app.clientes import repo as clientes_repo
from app.copiloto import sessao as sessao_do_copiloto
from app.copiloto.ferramentas.base import FerramentaDoCopiloto
from app.ia.ferramentas import registro
from app.plataforma.banco import fabrica_sessao

LIMITE_PROMPT = 20000


async def propor_agente_novo(
    empresa_id: str,
    nome: str,
    resumo: str,
    prompt: str,
    ferramentas: list[str] | None = None,
) -> str:
    """Propõe criar um agente novo para conversar no painel e no terminal (canal nativo).

    Nada é criado até o operador confirmar. Conectar o agente ao WhatsApp ou ao Chatwoot é outro
    passo, feito por ele no painel. Escreva o prompt inteiro, em português, dizendo quem o agente
    é, o que a empresa faz e como ele deve atender.

    Args:
        empresa_id: id da empresa, como veio de listar_empresas.
        nome: nome do agente, como o contato vai ver.
        resumo: uma frase dizendo ao operador o que este agente faz.
        prompt: prompt do agente, inteiro.
        ferramentas: ferramentas ligadas, com os nomes de listar_ferramentas.
    """
    try:
        procurada = uuid.UUID(empresa_id)
    except ValueError:
        return "empresa_id inválido. Chame listar_empresas para ver os ids que existem."
    async with fabrica_sessao()() as s:
        empresa = await clientes_repo.obter(s, procurada)
    if empresa is None:
        return "Empresa não encontrada. Chame listar_empresas para ver os ids que existem."
    if not nome.strip():
        return "O agente precisa de um nome."
    if ferramentas:
        desconhecidas = sorted(set(ferramentas) - set(registro.CATALOGO))
        if desconhecidas:
            return (
                f"Estas ferramentas não existem: {', '.join(desconhecidas)}. "
                "Chame listar_ferramentas e use os nomes de lá."
            )

    proposta = await sessao_do_copiloto.anota_proposta(
        {
            "tipo": "agente_novo",
            "cliente_id": str(empresa.id),
            "titulo": f"Criar {nome.strip()} em {empresa.nome}",
            "resumo": resumo.strip(),
            "nome": nome.strip(),
            "ferramentas": ferramentas or [],
            "prompt": prompt[:LIMITE_PROMPT],
        }
    )
    return (
        f"Proposta {proposta['id']} registrada e mostrada ao operador. Nada foi criado ainda: ele"
        " precisa confirmar no painel. Diga em uma frase o que propôs e espere a resposta dele."
    )


FERRAMENTA = FerramentaDoCopiloto(
    nome="propor_agente_novo",
    descricao="propõe criar um agente novo no canal nativo",
    funcao=propor_agente_novo,
    escreve=True,
)
