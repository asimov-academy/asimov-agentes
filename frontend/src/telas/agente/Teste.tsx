import { useCallback, useEffect, useRef, useState } from "react";
import { api, ErroDaApi } from "../../api/cliente";
import { Botao } from "../../design/Botao";
import { Campo } from "../../design/Campo";
import { Carregando } from "../../design/Carregando";

/** A conversa de teste, pelo canal nativo. É o mesmo `asimov conversar` do terminal.
 *
 *  O agente responde de verdade, com o modelo e o prompt dele, e a resposta entra no consumo como
 *  qualquer outra. A tela diz isso: teste não é simulação, e uma resposta aqui custa como uma
 *  resposta lá.
 *
 *  A explicação fica só aqui, no lugar onde se escreve, e uma vez só: a ficha e o fim do onboarding
 *  diziam o mesmo por cima (auditoria de copy de 2026-09-18).
 */

type Fala = { de: "voce" | "agente"; texto: string };

export function Teste({
  agenteId,
  agente,
  primeiraMensagem,
}: {
  agenteId: string;
  agente: string;
  /** A sugestão que já vem escrita no campo, para o operador só apertar Enter. */
  primeiraMensagem?: string;
}) {
  const [conversa, setConversa] = useState<string | null>(null);
  const [falas, setFalas] = useState<Fala[]>([]);
  const [texto, setTexto] = useState(primeiraMensagem ?? "");
  const [esperando, setEsperando] = useState(false);
  const [erro, setErro] = useState("");
  const proxima = useRef(0);
  const fim = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fim.current?.scrollIntoView({ block: "end" });
  }, [falas, esperando]);

  const le = useCallback(
    async (nome: string) => {
      try {
        const leitura = await api.leTeste(agenteId, nome, proxima.current);
        if (leitura.mensagens.length > 0) {
          proxima.current = leitura.proxima;
          setFalas((antes) => [
            ...antes,
            ...leitura.mensagens.map((m) => ({ de: "agente" as const, texto: String(m.texto ?? "") })),
          ]);
        }
        return leitura.respondendo || leitura.digitando;
      } catch (problema) {
        setErro(problema instanceof ErroDaApi ? problema.message : String(problema));
        return false;
      }
    },
    [agenteId],
  );

  // Enquanto o agente está respondendo, pergunta de novo: é o mesmo laço do terminal.
  useEffect(() => {
    if (!conversa || !esperando) return;
    let vivo = true;
    const laco = setInterval(async () => {
      const aindaVem = await le(conversa);
      if (!aindaVem && vivo) {
        setEsperando(false);
      }
    }, 1200);
    return () => {
      vivo = false;
      clearInterval(laco);
    };
  }, [conversa, esperando, le]);

  async function manda() {
    const mensagem = texto.trim();
    if (!mensagem || esperando) return;
    setErro("");
    setFalas((antes) => [...antes, { de: "voce", texto: mensagem }]);
    setTexto("");
    setEsperando(true);
    try {
      const enviada = await api.mandaTeste(agenteId, mensagem, conversa ?? undefined);
      setConversa(enviada.conversa);
    } catch (problema) {
      setErro(problema instanceof ErroDaApi ? problema.message : String(problema));
      setEsperando(false);
    }
  }

  return (
    <div className="flex flex-col">
      <div className="flex max-h-72 min-h-[12rem] flex-col gap-3 overflow-y-auto rounded-lg border border-borda bg-void p-4">
        {falas.length === 0 && !esperando && (
          <p className="text-sm text-dim">
            Escreva algo e veja {agente} responder. Ele usa o modelo e o prompt de verdade, e a
            resposta entra no consumo como qualquer outra.
          </p>
        )}
        {falas.map((f, i) => (
          <div key={i} className={`flex ${f.de === "voce" ? "justify-end" : "justify-start"}`}>
            <p
              className={`max-w-[85%] rounded-lg border px-3 py-2 text-sm leading-snug ${
                f.de === "voce"
                  ? "border-ciano/30 bg-ciano/5 text-texto"
                  : "border-borda bg-surface text-texto"
              }`}
            >
              {f.texto}
            </p>
          </div>
        ))}
        {esperando && (
          <div className="flex justify-start">
            <span className="rounded-full border border-borda bg-surface px-3 py-1.5">
              <Carregando tipo="digitando" o_que={`${agente} está respondendo`} compacto />
            </span>
          </div>
        )}
        <div ref={fim} />
      </div>

      <form
        className="mt-3 flex items-end gap-3"
        onSubmit={(e) => {
          e.preventDefault();
          manda();
        }}
      >
        <div className="min-w-0 flex-1">
          <Campo
            value={texto}
            onChange={(e) => setTexto(e.target.value)}
            placeholder="escreva como um contato escreveria"
            aria-label="Mensagem para o agente"
          />
        </div>
        <Botao tom="acento" pequeno icone="comm-send" ocupado={esperando} type="submit">
          Enviar
        </Botao>
      </form>

      {erro && <p className="mt-2 text-sm text-perigo">{erro}</p>}
    </div>
  );
}
