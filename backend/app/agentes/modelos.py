import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.ia import ferramentas
from app.plataforma.banco import Base, ComCriacao, ComId, agora



class Agente(ComId, ComCriacao, Base):
    __tablename__ = "agente"
    __table_args__ = (UniqueConstraint("cliente_id", "slug"),)

    cliente_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cliente.id"), index=True)
    nome: Mapped[str] = mapped_column(String(200))
    slug: Mapped[str] = mapped_column(String(200))
    canal: Mapped[str] = mapped_column(String(20))

    credenciais_cifradas: Mapped[str] = mapped_column(Text)
    token_webhook_hash: Mapped[str] = mapped_column(String(64), unique=True)
    token_webhook_cifrado: Mapped[str] = mapped_column(Text)

    arquivo_prompt: Mapped[str] = mapped_column(String(500))
    arquivo_prompt_handoff: Mapped[str] = mapped_column(String(500))

    modelo_conversa: Mapped[str] = mapped_column(String(100))
    modelo_fallback: Mapped[str | None] = mapped_column(String(100))
    modelo_auxiliar: Mapped[str] = mapped_column(String(100))
    modelo_visao: Mapped[str] = mapped_column(String(100))
    modelo_transcricao: Mapped[str] = mapped_column(String(100))

    buffer_segundos: Mapped[int] = mapped_column(default=8)
    max_mensagens_por_resposta: Mapped[int] = mapped_column(default=3)
    digitacao_caracteres_por_segundo: Mapped[int] = mapped_column(default=6, server_default="6")
    """Velocidade com que o agente "digita": define quanto o digitando dura antes de cada mensagem."""
    digitacao_maximo_segundos: Mapped[int] = mapped_column(default=20, server_default="20")
    ferramentas: Mapped[list[str]] = mapped_column(
        JSONB, default=lambda: list(ferramentas.PADRAO), server_default="[]"
    )
    """Nomes do catálogo de `ia/ferramentas/registro.py` ligados neste agente."""

    tom: Mapped[str] = mapped_column(String(20), default="normal", server_default="normal")
    """Como o agente fala: `formal`, `normal` ou `descontraido`. Muda só o jeito, nunca o conteúdo."""

    transfere_para_humano: Mapped[bool] = mapped_column(default=True, server_default="true")
    """Com isto desligado, a tool de handoff nem é oferecida ao modelo: o agente atende sozinho até
    o fim. Quem vende sem equipe de atendimento não quer o agente prometendo uma pessoa que não existe."""

    restringe_temas: Mapped[bool] = mapped_column(default=True, server_default="false")
    """O agente só fala do que é da empresa dele e devolve qualquer outro assunto para o atendimento.

    Nasce ligado: quem contrata um agente de atendimento não quer o modelo respondendo receita de
    bolo em nome da empresa. O `server_default` segue `false` de propósito, como o do emoji: agente
    criado antes disto continua do jeito que nasceu, e só muda se o operador desligar ou ligar."""

    emojis: Mapped[str] = mapped_column(String(10), default="nenhum", server_default="livre")
    """Quanto o agente usa emoji: `nenhum`, `pouco`, `medio` ou `muito`. `livre` é o que os agentes
    criados antes desta escolha mantêm, e para eles a plataforma não diz nada sobre emoji."""

    contatos_permitidos: Mapped[list[str]] = mapped_column(JSONB, default=list, server_default="[]")
    """Telefones que o agente atende, só dígitos. Lista vazia é o normal: atende quem mandar mensagem.
    Serve para testar um número novo sem responder a qualquer pessoa que escreva para ele."""

    perfil: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default="{}")
    """O que a aba Trabalho perguntou: `funcao`, `publico`, `site` e `sobre_empresa`. É daqui que
    sai o `persona.md` gerado. Fica no agente, nunca na empresa: é o que impede um prompt de
    atravessar de uma empresa para outra. Vazio no agente criado antes da aba existir."""

    assina_nome: Mapped[bool] = mapped_column(default=False, server_default="false")
    """O agente acrescenta o próprio nome no fim da resposta."""

    handoff_destino: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    retomada_automatica_horas: Mapped[int | None]

    ativo: Mapped[bool] = mapped_column(default=True)
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=agora, onupdate=agora
    )
    removido_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
