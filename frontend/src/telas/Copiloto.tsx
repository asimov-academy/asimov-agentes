import { useCallback, useEffect, useRef, useState } from "react";
import {
  api,
  type EstadoDoCopiloto,
  type PropostaDoCopiloto,
  type SessaoDoCopiloto,
} from "../api/cliente";
import { Aviso } from "../design/Aviso";
import { Botao } from "../design/Botao";
import { Icone } from "../design/Icone";
import { Modal } from "../design/Modal";

/** O copiloto do painel, no popup grande de sempre.
 *
 *  Duas coisas separam esta tela de um chat qualquer:
 *
 *  - **O copiloto não muda nada sozinho.** O que ele propõe aparece como um cartão com o que vai
 *    mudar e dois botões. Enquanto ninguém clica, a plataforma segue igual.
 *  - **Sem conta de IA vinculada ele nem aparece como chat**: a tela explica o que ele faria e
 *    mostra o comando do terminal, porque o login do CLI acontece na VPS, não no navegador.
 *
 *  O acompanhamento é por polling enquanto ele pensa, como a conversa de teste do agente.
 */
const INTERVALO_MS = 2000;

export function Copiloto({ aoFechar }: { aoFechar: () => void }) {
  const [estado, setEstado] = useState<EstadoDoCopiloto | null>(null);
  const [erro, setErro] = useState("");
  const [texto, setTexto] = useState("");
  const [ocupado, setOcupado] = useState("");
  const fim = useRef<HTMLDivElement>(null);

  const sessao = estado?.sessao ?? null;
  const pensando = sessao?.estado === "pensando";

  useEffect(() => {
    api
      .copiloto()
      .then(setEstado)
      .catch((problema) => setErro(problema.message));
  }, []);

  // Só enquanto ele pensa: parado, a tela não precisa perguntar nada ao servidor.
  useEffect(() => {
    if (!pensando) return;
    const relogio = setInterval(() => {
      api
        .copilotoSessao()
        .then((nova) =>
          setEstado((antes) => (antes ? { ...antes, sessao: nova } : antes)),
        )
        .catch(() => undefined);
    }, INTERVALO_MS);
    return () => clearInterval(relogio);
  }, [pensando]);

  useEffect(() => {
    // `?.()` porque nem todo ambiente tem a rolagem (o jsdom dos testes não tem).
    fim.current?.scrollIntoView?.({ block: "end" });
  }, [sessao?.mensagens.length, pensando]);

  const guarda = useCallback((nova: SessaoDoCopiloto) => {
    setEstado((antes) => (antes ? { ...antes, sessao: nova } : antes));
  }, []);

  async function fala() {
    const pedido = texto.trim();
    if (!pedido || pensando) return;
    setTexto("");
    setErro("");
    try {
      guarda(await api.copilotoFala(pedido));
    } catch (problema) {
      setErro((problema as Error).message);
      setTexto(pedido);
    }
  }

  async function decide(proposta: PropostaDoCopiloto, aplicar: boolean) {
    setOcupado(proposta.id);
    setErro("");
    try {
      guarda(await api.copilotoDecide(proposta.id, aplicar));
    } catch (problema) {
      setErro((problema as Error).message);
    } finally {
      setOcupado("");
    }
  }

  async function recomeca() {
    try {
      guarda(await api.copilotoRecomeca());
    } catch (problema) {
      setErro((problema as Error).message);
    }
  }

  const vinculo = estado?.vinculo;
  const pendentes = (sessao?.propostas ?? []).filter(
    (p) => p.situacao === "aguardando",
  );

  return (
    <Modal
      titulo="Copiloto"
      subtitulo={
        vinculo?.vinculada
          ? `Peça em português e ele configura a plataforma. Rodando pelo ${vinculo.nome}.`
          : "O assistente que configura a plataforma conversando com você."
      }
      aoFechar={aoFechar}
      rodape={
        vinculo?.vinculada ? (
          <>
            <Botao
              tom="fantasma"
              pequeno
              icone="sys-refresh"
              onClick={recomeca}
            >
              Recomeçar
            </Botao>
            <Botao tom="fantasma" onClick={aoFechar}>
              Fechar
            </Botao>
          </>
        ) : undefined
      }
    >
      {erro && (
        <div className="mb-5">
          <Aviso tom="erro" titulo="não deu certo">
            {erro}
          </Aviso>
        </div>
      )}

      {!estado ? (
        <p className="text-sm text-muted">abrindo o copiloto…</p>
      ) : !vinculo?.vinculada ? (
        <SemConta
          nome={vinculo?.nome ?? ""}
          assinatura={vinculo?.assinatura ?? ""}
          comando={vinculo?.comando ?? "asimov ia"}
        />
      ) : (
        <div className="flex flex-col gap-5">
          <div className="max-h-[46vh] min-h-[16rem] overflow-y-auto pr-1">
            {sessao && sessao.mensagens.length === 0 ? (
              <Comeco />
            ) : (
              <ol className="flex flex-col gap-4">
                {sessao?.mensagens.map((m, i) => (
                  <li
                    key={`${m.em}-${i}`}
                    className={m.autor === "operador" ? "flex justify-end" : ""}
                  >
                    <Fala autor={m.autor} texto={m.texto} />
                  </li>
                ))}
              </ol>
            )}
            {pensando && (
              <p className="mt-4 flex items-center gap-2 text-sm text-muted">
                <Icone nome="sys-girando" className="animate-spin" />
                pensando e lendo a plataforma…
              </p>
            )}
            {sessao?.erro && (
              <div className="mt-4">
                <Aviso tom="atencao" titulo="o copiloto parou">
                  {sessao.erro}
                </Aviso>
              </div>
            )}
            <div ref={fim} />
          </div>

          {pendentes.map((proposta) => (
            <Proposta
              key={proposta.id}
              proposta={proposta}
              ocupado={ocupado === proposta.id}
              aoDecidir={decide}
            />
          ))}

          <div className="flex items-end gap-3">
            <textarea
              value={texto}
              onChange={(e) => setTexto(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  void fala();
                }
              }}
              rows={2}
              placeholder="Ex: deixe a Bella mais objetiva e ligue a calculadora nela"
              aria-label="o que você quer que o copiloto faça"
              className="min-h-[3.25rem] flex-1 resize-y rounded-md border border-dim bg-panel p-3 text-sm text-texto placeholder:text-dim focus:border-ciano focus:outline-none"
            />
            <Botao
              tom="solido"
              icone="comm-send"
              onClick={fala}
              disabled={pensando || !texto.trim()}
            >
              Enviar
            </Botao>
          </div>
        </div>
      )}
    </Modal>
  );
}

function Comeco() {
  return (
    <div className="flex flex-col gap-3 text-sm text-muted">
      <p className="text-texto">
        Peça em português. Ele lê a plataforma antes de propor.
      </p>
      <ul className="flex flex-col gap-2">
        {[
          "Crie um agente de vendas para a Loja Exemplo",
          "Deixe o prompt da Bella mais curto e objetivo",
          "Quais agentes estão sem ferramenta ligada?",
        ].map((exemplo) => (
          <li
            key={exemplo}
            className="rounded-md border border-borda bg-panel px-3 py-2"
          >
            {exemplo}
          </li>
        ))}
      </ul>
      <p>Toda mudança aparece aqui para você confirmar antes de valer.</p>
    </div>
  );
}

function Fala({ autor, texto }: { autor: string; texto: string }) {
  if (autor === "sistema") {
    return (
      <p className="flex items-center gap-2 text-xs text-ok">
        <Icone nome="act-check" tamanho={14} />
        {texto}
      </p>
    );
  }
  const meu = autor === "operador";
  return (
    <div
      className={`max-w-[80%] whitespace-pre-wrap rounded-lg px-4 py-3 text-sm leading-relaxed ${
        meu ? "bg-texto text-void" : "border border-borda bg-panel text-texto"
      }`}
    >
      {texto}
    </div>
  );
}

function Proposta({
  proposta,
  ocupado,
  aoDecidir,
}: {
  proposta: PropostaDoCopiloto;
  ocupado: boolean;
  aoDecidir: (proposta: PropostaDoCopiloto, aplicar: boolean) => void;
}) {
  const campos = Object.entries(proposta.campos ?? {});
  return (
    <section className="relative rounded-lg border border-ciano/40 bg-panel p-5 pl-6">
      <span
        aria-hidden="true"
        className="absolute inset-y-4 left-2.5 w-0.5 rounded-full bg-ciano"
      />
      <span className="rotulo text-ciano">precisa da sua confirmação</span>
      <h4 className="mt-2 text-base font-semibold text-texto">
        {proposta.titulo}
      </h4>
      <p className="mt-1 text-sm text-muted">{proposta.resumo}</p>

      {campos.length > 0 && (
        <dl className="mt-4 grid gap-2 text-sm md:grid-cols-2">
          {campos.map(([campo, valor]) => (
            <div
              key={campo}
              className="rounded-md border border-borda bg-surface px-3 py-2"
            >
              <dt className="rotulo">{campo.replace(/_/g, " ")}</dt>
              <dd className="mt-1 break-words text-texto">{String(valor)}</dd>
            </div>
          ))}
        </dl>
      )}

      {proposta.prompt && (
        <details className="mt-4 rounded-md border border-borda bg-surface px-3 py-2">
          <summary className="cursor-pointer text-sm text-muted">
            ver o prompt proposto
          </summary>
          <pre className="mt-2 max-h-56 overflow-y-auto whitespace-pre-wrap font-mono text-xs text-texto">
            {proposta.prompt}
          </pre>
        </details>
      )}

      <div className="mt-5 flex flex-wrap gap-3">
        <Botao
          tom="solido"
          pequeno
          icone="act-check"
          ocupado={ocupado}
          onClick={() => aoDecidir(proposta, true)}
        >
          Confirmar
        </Botao>
        <Botao
          tom="fantasma"
          pequeno
          icone="act-cancel"
          disabled={ocupado}
          onClick={() => aoDecidir(proposta, false)}
        >
          Agora não
        </Botao>
      </div>
    </section>
  );
}

function SemConta({
  nome,
  assinatura,
  comando,
}: {
  nome: string;
  assinatura: string;
  comando: string;
}) {
  return (
    <div className="flex flex-col gap-5">
      <p className="text-sm leading-relaxed text-muted">
        Com a sua conta do <span className="text-texto">{nome}</span> vinculada,
        o copiloto cria agente, reescreve prompt e liga ferramenta conversando
        com você, aqui mesmo. Ele roda pela sua assinatura ({assinatura}), sem
        chave de API e sem custo por token.
      </p>
      <div className="rounded-lg border border-borda bg-panel p-5">
        <span className="rotulo">no terminal da VPS</span>
        <pre className="mt-2 font-mono text-sm text-ciano">{comando}</pre>
        <p className="mt-3 text-sm text-muted">
          O login acontece no terminal porque é o CLI que guarda a sua
          credencial. Depois de vincular, o copiloto aparece aqui.
        </p>
      </div>
    </div>
  );
}
