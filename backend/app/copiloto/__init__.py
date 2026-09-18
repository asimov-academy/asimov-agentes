"""Copiloto do painel: o operador pede em português e a plataforma se configura.

O motor é o CLI de código que o operador escolheu na instalação (Claude Code ou Codex), rodando
pela assinatura dele. Três decisões seguram o resto do módulo:

- **A assinatura é a única forma de pagar.** Chave de API não liga o copiloto: quem tem assinatura
  já pagou, e cobrar por token do lado de cá seria cobrar duas vezes. `vinculo.py` só conta o que o
  `asimov ia` gravou no `.env`; o segredo do login fica na pasta do CLI, montada no contêiner.
- **O CLI nunca escreve na plataforma.** As ferramentas de leitura respondem na hora; as de escrita
  apenas registram uma proposta. Quem aplica é o backend, depois de o operador confirmar no painel.
  Assim nenhuma frase enfiada numa conversa de contato consegue mudar um agente sozinha.
- **Turno fora da requisição.** O painel enfileira, o worker do copiloto executa o CLI e grava o
  andamento no Redis, e o painel acompanha por polling, como já faz a conversa de teste do agente.
"""
