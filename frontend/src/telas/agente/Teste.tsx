import { useCallback, useEffect, useRef, useState } from "react";
import { api, ErroDaApi } from "../../api/cliente";
import { BotaoIcone } from "../../design/BotaoIcone";
import { Carregando } from "../../design/Carregando";
import { Icone } from "../../design/Icone";

/** A conversa de teste, pelo canal nativo. É o mesmo `asimov conversar` do terminal.
 *
 *  O agente responde de verdade, com o modelo e o prompt dele, e a resposta entra no consumo como
 *  qualquer outra. A tela diz isso, em uma frase: teste não é simulação.
 *
 *  Testar de verdade inclui o que o contato manda no WhatsApp: áudio gravado na hora, imagem e
 *  documento. O arquivo segue o caminho de qualquer canal (grava, agenda, o turno lê), então o que
 *  o operador vê aqui é o que o cliente dele vai ver lá.
 */

type Fala = { de: "voce" | "agente"; texto: string; arquivo?: { nome: string; tipo: string } };

const ICONE_DO_ARQUIVO = {
  audio: "cont-audio",
  imagem: "cont-image",
  documento: "cont-doc",
} as const;

function tipoDoArquivo(mime: string): keyof typeof ICONE_DO_ARQUIVO {
  if (mime.startsWith("audio/")) return "audio";
  if (mime.startsWith("image/")) return "imagem";
  return "documento";
}

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
  const [anexo, setAnexo] = useState<File | null>(null);
  const [gravando, setGravando] = useState(false);
  const [esperando, setEsperando] = useState(false);
  const [erro, setErro] = useState("");
  const proxima = useRef(0);
  const fim = useRef<HTMLDivElement>(null);
  const seletor = useRef<HTMLInputElement>(null);
  const gravador = useRef<MediaRecorder | null>(null);

  useEffect(() => {
    fim.current?.scrollIntoView({ block: "end" });
  }, [falas, esperando]);

  // Sair da aba no meio da gravação solta o microfone.
  useEffect(() => () => gravador.current?.stream.getTracks().forEach((t) => t.stop()), []);

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

  async function manda(arquivo: File | null = anexo) {
    const mensagem = texto.trim();
    if ((!mensagem && !arquivo) || esperando) return;
    setErro("");
    setFalas((antes) => [
      ...antes,
      {
        de: "voce",
        texto: mensagem,
        arquivo: arquivo ? { nome: arquivo.name, tipo: tipoDoArquivo(arquivo.type) } : undefined,
      },
    ]);
    setTexto("");
    setAnexo(null);
    setEsperando(true);
    try {
      const enviada = arquivo
        ? await api.mandaArquivoDeTeste(agenteId, arquivo, mensagem, conversa ?? undefined)
        : await api.mandaTeste(agenteId, mensagem, conversa ?? undefined);
      setConversa(enviada.conversa);
    } catch (problema) {
      setErro(problema instanceof ErroDaApi ? problema.message : String(problema));
      setEsperando(false);
    }
  }

  async function grava() {
    setErro("");
    try {
      const som = await navigator.mediaDevices.getUserMedia({ audio: true });
      const novo = new MediaRecorder(som);
      const pedacos: Blob[] = [];
      novo.ondataavailable = (e) => pedacos.push(e.data);
      novo.onstop = () => {
        som.getTracks().forEach((t) => t.stop());
        setGravando(false);
        const tipo = novo.mimeType || "audio/webm";
        const extensao = tipo.includes("mp4") ? "m4a" : tipo.includes("ogg") ? "ogg" : "webm";
        // Parou, mandou: é assim no WhatsApp, e é o WhatsApp que se está ensaiando aqui.
        manda(new File(pedacos, `audio.${extensao}`, { type: tipo }));
      };
      gravador.current = novo;
      novo.start();
      setGravando(true);
    } catch {
      setErro("O navegador não liberou o microfone.");
    }
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div
        role="log"
        aria-live="polite"
        aria-label={`Conversa com ${agente}`}
        className="flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto rounded-lg border border-borda bg-void p-4"
      >
        {falas.length === 0 && !esperando && (
          // Uma frase só, e é a do custo: teste não é simulação.
          <p className="text-sm text-dim">
            Teste de verdade: cada resposta de {agente} conta no consumo.
          </p>
        )}
        {falas.map((f, i) => (
          <div key={i} className={`flex ${f.de === "voce" ? "justify-end" : "justify-start"}`}>
            <div
              className={`max-w-[85%] whitespace-pre-line rounded-lg border px-3 py-2 text-sm leading-snug ${
                f.de === "voce"
                  ? "border-ciano/30 bg-ciano/5 text-texto"
                  : "border-borda bg-surface text-texto"
              }`}
            >
              {f.arquivo && (
                <span className="flex items-center gap-2 text-muted">
                  <Icone nome={ICONE_DO_ARQUIVO[f.arquivo.tipo as keyof typeof ICONE_DO_ARQUIVO]} tamanho={16} />
                  <span className="truncate">{f.arquivo.nome}</span>
                </span>
              )}
              {f.texto}
            </div>
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

      {anexo && (
        <div className="mt-3 flex items-center gap-2 text-sm text-muted">
          <Icone nome={ICONE_DO_ARQUIVO[tipoDoArquivo(anexo.type)]} tamanho={16} />
          <span className="min-w-0 flex-1 truncate">{anexo.name}</span>
          <BotaoIcone icone="sys-close" rotulo="Tirar o anexo" onClick={() => setAnexo(null)} />
        </div>
      )}

      {/* Uma barra só: anexar e gravar à esquerda, o texto no meio, enviar à direita. */}
      <form
        className="mt-3 flex shrink-0 items-end gap-1 rounded-lg border border-borda bg-surface p-1 transition-colors focus-within:border-ciano"
        onSubmit={(e) => {
          e.preventDefault();
          manda();
        }}
      >
        <input
          ref={seletor}
          type="file"
          hidden
          accept="image/*,audio/*,application/pdf,text/plain"
          onChange={(e) => {
            setAnexo(e.target.files?.[0] ?? null);
            e.target.value = "";
          }}
        />
        <BotaoIcone
          icone="act-attach"
          alinha="inicio"
          rotulo="Anexar"
          explica="Imagem, áudio, PDF ou texto, até 20 MB."
          disabled={esperando || gravando}
          onClick={() => seletor.current?.click()}
        />
        {gravando ? (
          <span role="status" className="flex min-h-11 flex-1 items-center gap-2 px-2 text-sm text-perigo">
            <span className="h-2 w-2 animate-pulse rounded-full bg-perigo" />
            Gravando
          </span>
        ) : (
          // Enter envia e Shift+Enter quebra a linha, como em todo chat.
          <textarea
            rows={1}
            value={texto}
            onChange={(e) => setTexto(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
                e.preventDefault();
                manda();
              }
            }}
            placeholder={anexo ? "legenda (opcional)" : "escreva como um contato"}
            aria-label="Mensagem"
            className="max-h-32 min-h-11 min-w-0 flex-1 resize-none bg-transparent px-2 py-2.5 text-sm text-texto placeholder:text-dim focus:outline-none focus-visible:ring-0"
          />
        )}
        {/* Com texto ou anexo, o botão é enviar. Vazio, é o microfone, como no WhatsApp. */}
        {gravando ? (
          <BotaoIcone
            icone="sys-stop"
            tom="perigo"
            rotulo="Parar e enviar"
            onClick={() => gravador.current?.stop()}
          />
        ) : texto.trim() || anexo ? (
          <BotaoIcone
            type="submit"
            icone="comm-send"
            tom="acento"
            rotulo="Enviar"
            explica="Enter envia. Shift+Enter quebra a linha."
            disabled={esperando}
          />
        ) : (
          <BotaoIcone
            icone="cont-audio"
            rotulo="Gravar áudio"
            explica="Grave, pare e ele vai como áudio de WhatsApp."
            disabled={esperando}
            onClick={grava}
          />
        )}
      </form>

      {erro && (
        <p role="alert" className="mt-2 text-sm text-perigo">
          {erro}
        </p>
      )}
    </div>
  );
}
