import { useCallback, useEffect, useState } from "react";
import {
  api,
  ErroDaApi,
  SemSessao,
  type Conversa,
  type ConversaAberta,
} from "../api/cliente";
import { Busca } from "../design/Busca";
import { Segmentos } from "../design/Segmentos";
import { Aviso } from "../design/Aviso";
import { Botao } from "../design/Botao";
import { Cabecalho } from "../design/Cabecalho";
import { Carregando } from "../design/Carregando";
import { Icone } from "../design/Icone";
import { Marca } from "../design/Marca";
import { Selo } from "../design/Selo";
import { Vazio } from "../design/Vazio";
import { CANAIS, ROTULO_DO_CANAL } from "./agente/canais";

/** A tela de Chat: a lista à esquerda e a conversa aberta à direita.
 *
 *  Duas colunas, e não popup: aqui o operador compara uma conversa com a lista enquanto lê. O popup
 *  é a regra da configuração do agente, que é outra coisa.
 *
 *  Conteúdo de conversa aparece no navegador por decisão registrada em spec/decisoes.md. Não existe
 *  exportação, e a página leva `noindex`.
 */

const SITUACOES = [
  { rotulo: "Todas", valor: "" },
  { rotulo: "Com o agente", valor: "agente" },
  { rotulo: "Com uma pessoa", valor: "humano" },
] as const;

const NOME_DO_AUTOR: Record<string, string> = {
  contato: "contato",
  agente: "agente",
  atendente: "atendente",
  sistema: "sistema",
};

/** Mensagem que é arquivo, e não texto, aparece pelo que ela é. O tipo cru (`audio`, `documento`)
 *  vem do canal e não é palavra de tela. */
const NOME_DO_TIPO: Record<string, string> = {
  audio: "áudio",
  imagem: "imagem",
  video: "vídeo",
  documento: "arquivo",
};

const hora = (iso: string) =>
  new Date(iso).toLocaleString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });

export function Chat() {
  const [conversas, setConversas] = useState<Conversa[] | null>(null);
  const [status, setStatus] = useState("");
  const [aberta, setAberta] = useState<ConversaAberta | null>(null);
  const [abrindo, setAbrindo] = useState("");
  const [erro, setErro] = useState("");
  const [devolvendo, setDevolvendo] = useState(false);
  // A lupa filtra a lista que já está na tela; a consulta continua trazendo as conversas recentes.
  const [filtro, setFiltro] = useState("");

  const busca = useCallback(() => {
    setErro("");
    api
      .conversas({ status: status || undefined })
      .then(setConversas)
      .catch((problema) => {
        if (problema instanceof SemSessao) throw problema;
        setErro(problema.message);
      });
  }, [status]);

  useEffect(busca, [busca]);

  const abre = useCallback(async (id: string) => {
    setAbrindo(id);
    setAberta(null);
    try {
      setAberta(await api.conversa(id));
    } catch (problema) {
      setErro(problema instanceof ErroDaApi ? problema.message : String(problema));
    } finally {
      setAbrindo("");
    }
  }, []);

  async function devolve() {
    if (!aberta) return;
    setDevolvendo(true);
    try {
      await api.retomaConversa(aberta.id);
      await abre(aberta.id);
      busca();
    } catch (problema) {
      setErro(problema instanceof ErroDaApi ? problema.message : String(problema));
    } finally {
      setDevolvendo(false);
    }
  }

  const marcaDaAberta = aberta ? CANAIS[aberta.canal]?.marca : undefined;
  const procurado = filtro.trim().toLowerCase();
  const achadas = (conversas ?? []).filter((c) =>
    !procurado
      ? true
      : [c.contato, c.telefone, c.agente, c.empresa].some((campo) =>
          (campo ?? "").toLowerCase().includes(procurado),
        ),
  );

  return (
    <>
      <Cabecalho
        titulo="Conversas"
        contexto={
          conversas !== null && achadas.length > 0
            ? `${achadas.length} ${achadas.length === 1 ? "conversa recente" : "conversas recentes"}`
            : undefined
        }
        acoes={
          <>
          <Busca
            valor={filtro}
            aoMudar={setFiltro}
            rotulo="Buscar conversa"
            placeholder="contato, agente ou empresa"
          />
          <Segmentos
            rotulo="Situação"
            opcoes={SITUACOES.map((s) => ({ rotulo: s.rotulo, valor: s.valor }))}
            valor={status}
            aoMudar={setStatus}
          />
          </>
        }
      />

      {erro && (
        <div className="mt-6">
          <Aviso tom="erro" titulo="não deu para carregar as conversas">
            <p>{erro}</p>
            <div className="mt-4">
              <Botao icone="sys-refresh" pequeno onClick={busca}>
                Tentar de novo
              </Botao>
            </div>
          </Aviso>
        </div>
      )}

      <div className="mt-8 grid gap-6 lg:grid-cols-[20rem_1fr]">
        <div className="min-w-0">
          {conversas === null ? (
            // Com o erro em cima, o "buscando conversas" embaixo diz o contrário dele: quem falha
            // para de procurar, e a saída é o Tentar de novo.
            !erro && <Carregando tipo="pontos" o_que="buscando conversas" />
          ) : achadas.length === 0 ? (
            procurado ? (
              <Vazio titulo="nenhuma conversa com esse nome" icone="sys-search" />
            ) : (
              <Vazio titulo="nenhuma conversa ainda" icone="comm-chat">
                Converse com um agente pelo menu dele, na lista de agentes.
              </Vazio>
            )
          ) : (
            <ul className="flex flex-col gap-1">
              {achadas.map((c) => {
                const marca = CANAIS[c.canal]?.marca;
                return (
                  <li key={c.id}>
                    <button
                      onClick={() => abre(c.id)}
                      className={`relative w-full rounded-md py-3 pl-4 pr-2 text-left transition-colors hover:bg-surface ${
                        aberta?.id === c.id ? "bg-surface" : ""
                      }`}
                    >
                      {aberta?.id === c.id && (
                        <span
                          aria-hidden="true"
                          className="absolute inset-y-2 left-1 w-0.5 rounded-full bg-ciano"
                        />
                      )}
                      <span className="flex items-baseline justify-between gap-3">
                        <span className="truncate text-sm text-texto">
                          {c.contato ?? c.telefone ?? "sem nome"}
                        </span>
                        <span className="tecnico shrink-0 text-[0.65rem] text-dim">
                          {hora(c.atualizado_em)}
                        </span>
                      </span>
                      <span className="mt-0.5 flex items-center gap-1.5 text-sm text-muted">
                        {marca && <Marca nome={marca} tamanho={13} />}
                        <span className="truncate">
                          {c.agente}, {ROTULO_DO_CANAL(c.canal)}
                        </span>
                      </span>
                      {c.status === "humano" && (
                        <span className="mt-1 inline-block">
                          <Selo tom="atencao">com uma pessoa</Selo>
                        </span>
                      )}
                    </button>
                  </li>
                );
              })}
            </ul>
          )}
        </div>

        <div className="min-w-0 rounded-lg border border-borda bg-surface">
          {abrindo ? (
            <Carregando tipo="anel" o_que="abrindo a conversa" />
          ) : !aberta ? (
            <div className="flex flex-col items-center justify-center gap-3 p-16 text-center">
              <span className="flex h-10 w-10 items-center justify-center rounded-full bg-dim/20">
                <Icone nome="comm-chat" tamanho={20} className="text-dim" />
              </span>
              <p className="text-sm text-muted">escolha uma conversa na lista</p>
            </div>
          ) : (
            <>
              <header className="flex flex-wrap items-center justify-between gap-4 border-b border-borda p-5">
                <div className="min-w-0">
                  <p className="text-base text-texto">
                    {aberta.contato ?? aberta.telefone ?? "sem nome"}
                  </p>
                  <p className="mt-0.5 flex items-center gap-1.5 text-sm text-muted">
                    {marcaDaAberta && <Marca nome={marcaDaAberta} tamanho={14} />}
                    <span className="truncate">
                      {aberta.agente}, {ROTULO_DO_CANAL(aberta.canal)}, em {aberta.empresa}
                    </span>
                  </p>
                </div>
                {aberta.status === "humano" && (
                  <Botao
                    tom="acento"
                    pequeno
                    icone="sys-undo"
                    ocupado={devolvendo}
                    onClick={devolve}
                  >
                    Devolver ao agente
                  </Botao>
                )}
              </header>

              <div className="flex max-h-[28rem] flex-col gap-3 overflow-y-auto p-5">
                {aberta.mensagens.length === 0 ? (
                  <p className="text-sm text-dim">Nenhuma mensagem guardada nesta conversa.</p>
                ) : (
                  aberta.mensagens.map((m) => {
                    const doContato = m.autor === "contato";
                    return (
                      <div
                        key={m.id}
                        className={`flex flex-col ${doContato ? "items-start" : "items-end"}`}
                      >
                        <p
                          className={`max-w-[80%] rounded-lg border px-3 py-2 text-sm leading-snug ${
                            doContato
                              ? "border-borda bg-void text-texto"
                              : "border-ciano/30 bg-ciano/5 text-texto"
                          }`}
                        >
                          {m.texto || m.texto_extraido || (
                            <span className="italic text-dim">
                              [{NOME_DO_TIPO[m.tipo] ?? "arquivo"}]
                            </span>
                          )}
                        </p>
                        <span className="mt-1 text-[0.625rem] text-dim">
                          {NOME_DO_AUTOR[m.autor] ?? m.autor},{" "}
                          <span className="font-mono">{hora(m.criado_em)}</span>
                        </span>
                      </div>
                    );
                  })
                )}
              </div>

              {aberta.turnos.length > 0 && (
                <div className="border-t border-borda p-5">
                  <p className="rotulo">o que cada resposta custou</p>
                  <ul className="mt-3 flex flex-col gap-2">
                    {aberta.turnos.slice(0, 8).map((t, i) => (
                      <li
                        key={i}
                        className="tecnico flex flex-wrap items-baseline justify-between gap-3"
                      >
                        <span className="text-muted">{t.modelo}</span>
                        <span className="text-dim">
                          {Math.round(t.latencia_ms / 100) / 10}s
                          {t.custo_estimado
                            ? `, US$ ${Number(t.custo_estimado).toFixed(4)}`
                            : ", sem preço"}
                        </span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </>
  );
}
