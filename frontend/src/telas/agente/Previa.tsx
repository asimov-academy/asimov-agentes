import { useEffect, useState } from "react";
import type { NivelDeEmoji } from "../../api/cliente";
import { Carregando } from "../../design/Carregando";

/** A prévia viva do onboarding: uma conversa de mentira onde o agente já responde com o que foi
 *  escolhido até aqui.
 *
 *  É o que responde sozinho a pergunta "o que essa escolha muda no meu agente", que hoje só o teste
 *  em produção responde. Nada disso chama a API nem gasta modelo: é texto montado no navegador a
 *  partir das escolhas, e a tela diz isso em uma linha para ninguém confundir com o agente de
 *  verdade.
 */

const EMOJI: Record<NivelDeEmoji, string> = {
  nenhum: "",
  pouco: " 🙂",
  medio: " 😊👍",
  muito: " 😄🎉👏",
};

const ABERTURA: Record<string, string> = {
  suporte: "Oi! Sou {nome} e cuido do suporte da {empresa}. O que aconteceu?",
  vendas: "Oi! Sou {nome}, da {empresa}. Posso te ajudar a escolher?",
  atendimento: "Oi! Sou {nome}, da {empresa}. Em que posso ajudar hoje?",
};

const RESPOSTA: Record<string, string> = {
  suporte: "Entendi. Vou verificar isso agora e já te digo o que encontrei.",
  vendas: "Boa escolha. Tenho duas opções que atendem isso, e a diferença é o prazo.",
  atendimento: "Claro, já verifico. Me confirma o nome completo, por favor?",
};

export type EscolhasDaPrevia = {
  nome: string;
  empresa: string;
  funcao: string;
  emojis: NivelDeEmoji;
  partes: number;
  buffer: number;
  busca: boolean;
};

function fala(modelo: string, escolhas: EscolhasDaPrevia): string {
  return modelo
    .replace("{nome}", escolhas.nome || "seu agente")
    .replace("{empresa}", escolhas.empresa || "sua empresa");
}

/** A resposta dividida em até `partes`, como o agente faz de verdade: por frase. */
function emPartes(texto: string, partes: number): string[] {
  const frases = texto.match(/[^.!?]+[.!?]*/g)?.map((f) => f.trim()) ?? [texto];
  if (partes <= 1 || frases.length <= 1) return [texto];
  const pedacos: string[] = [];
  const porParte = Math.ceil(frases.length / partes);
  for (let i = 0; i < frases.length; i += porParte) {
    pedacos.push(frases.slice(i, i + porParte).join(" "));
  }
  return pedacos.slice(0, partes);
}

export function Previa({ escolhas }: { escolhas: EscolhasDaPrevia }) {
  const [digitando, setDigitando] = useState(false);

  // Cada mudança faz o agente "digitar" de novo, no ritmo do buffer escolhido: é o que mostra o
  // efeito do tempo de espera sem precisar mandar mensagem de verdade.
  useEffect(() => {
    setDigitando(true);
    const t = setTimeout(() => setDigitando(false), Math.min(1200, escolhas.buffer * 120));
    return () => clearTimeout(t);
  }, [escolhas.nome, escolhas.funcao, escolhas.emojis, escolhas.partes, escolhas.buffer, escolhas.busca]);

  const sufixo = EMOJI[escolhas.emojis] ?? "";
  const abertura = fala(ABERTURA[escolhas.funcao] ?? ABERTURA.atendimento, escolhas) + sufixo;
  const resposta = fala(RESPOSTA[escolhas.funcao] ?? RESPOSTA.atendimento, escolhas);
  const partes = emPartes(resposta, escolhas.partes);

  return (
    <div className="flex h-full flex-col border border-borda bg-void p-5">
      <p className="rotulo">como ele vai soar</p>

      <div className="mt-4 flex flex-1 flex-col gap-3">
        <Bolha de="agente">{abertura}</Bolha>
        <Bolha de="contato">Oi, tudo bem? Preciso de uma ajuda aqui.</Bolha>

        {digitando ? (
          <Digitando />
        ) : (
          partes.map((parte, i) => (
            <Bolha key={i} de="agente">
              {parte}
              {i === partes.length - 1 ? sufixo : ""}
            </Bolha>
          ))
        )}

        {escolhas.busca && !digitando && (
          <Bolha de="agente">
            Procurei agora no site e a informação está lá: a garantia é de 12 meses.
          </Bolha>
        )}
      </div>

      <p className="mt-4 border-t border-borda pt-3 text-xs leading-snug text-dim">
        Conversa de mentira, montada no navegador. Nenhum modelo foi chamado e nada foi cobrado.
      </p>
    </div>
  );
}

function Bolha({ de, children }: { de: "agente" | "contato"; children: React.ReactNode }) {
  const doAgente = de === "agente";
  return (
    <div className={`flex ${doAgente ? "justify-start" : "justify-end"}`}>
      <p
        className={`max-w-[85%] border px-3 py-2 text-sm leading-snug ${
          doAgente ? "border-borda bg-surface text-texto" : "border-ciano/30 bg-ciano/5 text-texto"
        }`}
      >
        {children}
      </p>
    </div>
  );
}

/** O "Typing" do KINETIC dentro da bolha. O desenho mora no `Carregando`, que é onde vivem os
 *  estados de espera do design system: tela não desenha SVG à mão, e um teste confere isso. */
function Digitando() {
  return (
    <div className="flex justify-start">
      <span className="border border-borda bg-surface px-3 py-1.5">
        <Carregando tipo="digitando" o_que="o agente está digitando" compacto />
      </span>
    </div>
  );
}
