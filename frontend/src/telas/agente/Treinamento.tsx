import { useState } from "react";
import type { Agente } from "../../api/cliente";
import { Icone } from "../../design/Icone";
import type { ICONES } from "../../design/icones";

/** O treinamento do agente: o que ele sabe, além do prompt.
 *
 *  **Ainda não funciona.** A tela existe desenhada, e vazia de propósito: ela é o lugar combinado
 *  para a base de conhecimento (fase 6) e para o que vier junto dela, e ter o lugar antes da
 *  máquina evita que cada tipo de material nasça num canto diferente do painel.
 *
 *  Cada aba é uma forma de ensinar a mesma coisa: uma frase que o operador escreve, um site, um
 *  vídeo, um arquivo, ou uma base inteira compartilhada entre agentes. Todas terminam no mesmo
 *  lugar: trechos que o agente busca na hora de responder.
 */
type Fonte = {
  chave: string;
  rotulo: string;
  icone: keyof typeof ICONES;
  titulo: string;
  explica: string;
  exemplo: string;
};

const FONTES: Fonte[] = [
  {
    chave: "texto",
    rotulo: "Texto",
    icone: "comm-comment",
    titulo: "Ensinar por frase",
    explica:
      "Uma afirmação por vez, do jeito que você diria para alguém novo na equipe. É o caminho mais curto para corrigir uma resposta errada.",
    exemplo: "Ex: não trabalhamos com entrega fora do estado.",
  },
  {
    chave: "site",
    rotulo: "Site",
    icone: "cont-link",
    titulo: "Ensinar por site",
    explica:
      "O endereço de uma página ou do mapa do site inteiro. A plataforma lê o texto e reaproveita quando o conteúdo mudar.",
    exemplo: "Ex: https://suaempresa.com.br/produtos",
  },
  {
    chave: "video",
    rotulo: "Vídeo",
    icone: "cont-video",
    titulo: "Ensinar por vídeo",
    explica:
      "Um vídeo em que alguém já explicou o que o agente precisa saber. Vale a fala, transcrita.",
    exemplo: "Ex: o vídeo de apresentação do produto",
  },
  {
    chave: "documento",
    rotulo: "Documento",
    icone: "cont-doc",
    titulo: "Ensinar por documento",
    explica:
      "Tabela de preço, catálogo, manual, política de troca. PDF, DOCX, TXT ou MD, com o texto dividido em trechos.",
    exemplo: "Ex: tabela-de-precos.pdf",
  },
  {
    chave: "base",
    rotulo: "Base de conhecimento",
    icone: "nav-projects",
    titulo: "Conectar uma base",
    explica:
      "Uma base que já existe, montada uma vez e ligada em quantos agentes precisar. Muda num lugar e vale em todos.",
    exemplo: "Ex: a base da Loja Sul, usada por três agentes",
  },
];

export function Treinamento({ agente }: { agente: Agente }) {
  const [fonte, setFonte] = useState(FONTES[0]);

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center gap-x-2 gap-y-1 border-b border-borda">
        {FONTES.map((f) => (
          <button
            key={f.chave}
            onClick={() => setFonte(f)}
            aria-pressed={fonte.chave === f.chave}
            className={`-mb-px border-b-2 px-3 py-2 text-sm transition-colors ${
              fonte.chave === f.chave
                ? "border-ciano text-ciano"
                : "border-transparent text-muted hover:text-texto"
            }`}
          >
            {f.rotulo}
          </button>
        ))}
      </div>

      <section className="relative rounded-lg border border-borda bg-panel p-6">
        <span className="absolute right-4 top-4 rounded-full border border-borda px-2 py-0.5 text-[0.5625rem] uppercase tracking-[0.06em] text-dim">
          em breve
        </span>
        <div className="flex items-start gap-4">
          <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-md border border-borda text-ciano">
            <Icone nome={fonte.icone} tamanho={18} />
          </span>
          <div className="min-w-0">
            <h4 className="text-base font-semibold text-texto">{fonte.titulo}</h4>
            <p className="mt-1 text-sm leading-relaxed text-muted">{fonte.explica}</p>
            <p className="mt-3 font-mono text-xs text-dim">{fonte.exemplo}</p>
          </div>
        </div>
      </section>

      <p className="text-sm text-muted">
        Enquanto isto não existe, o que {agente.nome} sabe vem do prompt, na aba Trabalho, e do que
        ele busca na web quando a ferramenta está ligada.
      </p>
    </div>
  );
}
