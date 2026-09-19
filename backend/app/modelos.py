"""Importa todos os modelos para o Alembic e os testes enxergarem o schema inteiro."""

from app.acessos.modelos import AcessoCanal, ChaveProvedor
from app.agentes.modelos import Agente
from app.clientes.modelos import Cliente
from app.conhecimento.modelos import ConfiguracaoEmbeddings, Documento, Trecho
from app.consumo.modelos import Falha, Turno
from app.conversas.modelos import Contato, Conversa, Mensagem
from app.handoff.modelos import Handoff
from app.midia.modelos import Midia
from app.oportunidades.modelos import Etiqueta, EtapaFunil, Oportunidade, OportunidadeEtiqueta
from app.painel.modelos import EspacoTrabalho, UsuarioPainel
from app.plataforma.banco import Base

__all__ = ["AcessoCanal", "Agente", "Base", "ChaveProvedor", "Cliente", "Contato", "Conversa", "Documento", "EspacoTrabalho", "EtapaFunil", "Etiqueta", "Falha", "Handoff", "Mensagem", "Midia", "Oportunidade", "OportunidadeEtiqueta", "Trecho", "Turno", "UsuarioPainel"]
