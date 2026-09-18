import { useCallback, useEffect, useState } from "react";
import {
  api,
  ErroDaApi,
  SemSessao,
  type Conversa,
  type ConversaAberta,
  type Empresa,
} from "../api/cliente";
import { Aviso } from "../design/Aviso";
import { Botao } from "../design/Botao";
import { Carregando } from "../design/Carregando";
import { Selo } from "../design/Selo";
import { Vazio } from "../design/Vazio";
import { ROTULO_DO_CANAL } from "./agente/canais";

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
  { rotulo: "Com gente", valor: "humano" },
] as const;

const NOME_DO_AUTOR: Record<string, string> = {
  contato: "contato",
  agente: "agente",
  atendente: "atendente",
  sistema: "sistema",
};

const hora = (iso: string) =>
  new Date(iso).toLocaleString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });

export function Chat({
  empresas,
  empresa,
  aoTrocarEmpresa,
}: {
  empresas: Empresa[];
  empresa: string;
  aoTrocarEmpresa: (id: string) => void;
}) {
  const [conversas, setConversas] = useState<Conversa[] | null>(null);
  const [status, setStatus] = useState("");
  const [aberta, setAberta] = useState<ConversaAberta | null>(null);
  const [abrindo, setAbrindo] = useState("");
  const [erro, setErro] = useState("");
  const [devolvendo, setDevolvendo] = useState(false);

  const busca = useCallback(() => {
    setErro("");
    api
      .conversas({ empresa: empresa || undefined, status: status || undefined })
      .then(setConversas)
      .catch((problema) => {
        if (problema instanceof SemSessao) throw problema;
        setErro(problema.message);
      });
  }, [empresa, status]);

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

  return (
    <>
      <header className="flex flex-wrap items-end justify-between gap-6 border-b border-borda pb-6">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight text-texto md:text-5xl">
            Chat<span className="text-lime">.</span>
          </h1>
          <p className="mt-2 text-sm text-muted">
            {conversas === null ? "buscando" : `${conversas.length} conversas recentes`}
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          {empresas.length > 1 && (
            <select
              value={empresa}
              aria-label="Empresa"
              onChange={(e) => aoTrocarEmpresa(e.target.value)}
              className="border border-borda bg-surface px-4 py-2 font-mono text-xs uppercase tracking-[0.15em] text-muted transition-colors hover:text-texto focus:border-lime"
            >
              <option value="">Todas as empresas</option>
              {empresas.map((e) => (
                <option key={e.id} value={e.id}>
                  {e.nome}
                </option>
              ))}
            </select>
          )}
          <div className="flex border border-borda" role="group" aria-label="Situação">
            {SITUACOES.map((s) => (
              <button
                key={s.rotulo}
                onClick={() => setStatus(s.valor)}
                aria-pressed={status === s.valor}
                className={`px-4 py-2 font-mono text-xs uppercase tracking-[0.15em] transition-colors ${
                  status === s.valor ? "bg-texto text-void" : "text-muted hover:text-texto"
                }`}
              >
                {s.rotulo}
              </button>
            ))}
          </div>
        </div>
      </header>

      {erro && (
        <div className="mt-6">
          <Aviso tom="erro" titulo="algo não voltou">
            {erro}
          </Aviso>
        </div>
      )}

      <div className="mt-8 grid gap-6 lg:grid-cols-[20rem_1fr]">
        <div className="min-w-0">
          {conversas === null ? (
            <Carregando tipo="pontos" o_que="buscando conversas" />
          ) : conversas.length === 0 ? (
            <Vazio titulo="nenhuma conversa" icone="comm-chat">
              A primeira mensagem que chegar a um agente aparece aqui.
            </Vazio>
          ) : (
            <ul className="border-t border-borda">
              {conversas.map((c) => (
                <li key={c.id}>
                  <button
                    onClick={() => abre(c.id)}
                    className={`w-full border-b border-l-2 border-borda py-3 pl-3 text-left transition-colors hover:bg-surface ${
                      aberta?.id === c.id ? "border-l-lime bg-surface" : "border-l-transparent"
                    }`}
                  >
                    <span className="flex items-baseline justify-between gap-3">
                      <span className="truncate text-sm text-texto">
                        {c.contato ?? c.telefone ?? "sem nome"}
                      </span>
                      <span className="shrink-0 font-mono text-[0.65rem] text-dim">
                        {hora(c.atualizado_em)}
                      </span>
                    </span>
                    <span className="mt-0.5 block truncate text-sm text-muted">
                      {c.agente}, {ROTULO_DO_CANAL(c.canal)}
                    </span>
                    {c.status === "humano" && (
                      <span className="mt-1 inline-block">
                        <Selo tom="atencao">com gente</Selo>
                      </span>
                    )}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="min-w-0 border border-borda bg-surface">
          {abrindo ? (
            <Carregando tipo="anel" o_que="abrindo a conversa" />
          ) : !aberta ? (
            <div className="p-8">
              <Vazio titulo="escolha uma conversa" icone="comm-chat">
                O histórico, quem falou e o custo de cada turno aparecem aqui.
              </Vazio>
            </div>
          ) : (
            <>
              <header className="flex flex-wrap items-center justify-between gap-4 border-b border-borda p-5">
                <div className="min-w-0">
                  <p className="text-base text-texto">
                    {aberta.contato ?? aberta.telefone ?? "sem nome"}
                  </p>
                  <p className="mt-0.5 text-sm text-muted">
                    {aberta.agente}, {ROTULO_DO_CANAL(aberta.canal)}, em {aberta.empresa}
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
                          className={`max-w-[80%] border px-3 py-2 text-sm leading-snug ${
                            doContato
                              ? "border-borda bg-void text-texto"
                              : "border-lime/30 bg-lime/5 text-texto"
                          }`}
                        >
                          {m.texto || m.texto_extraido || `[${m.tipo}]`}
                        </p>
                        <span className="mt-1 font-mono text-[0.625rem] text-dim">
                          {NOME_DO_AUTOR[m.autor] ?? m.autor}, {hora(m.criado_em)}
                        </span>
                      </div>
                    );
                  })
                )}
              </div>

              {aberta.turnos.length > 0 && (
                <div className="border-t border-borda p-5">
                  <p className="rotulo">o que cada turno custou</p>
                  <ul className="mt-3 flex flex-col gap-2">
                    {aberta.turnos.slice(0, 8).map((t, i) => (
                      <li
                        key={i}
                        className="flex flex-wrap items-baseline justify-between gap-3 font-mono text-xs"
                      >
                        <span className="text-muted">{t.modelo}</span>
                        <span className="text-dim">
                          {t.tokens_entrada + t.tokens_saida} tokens, {Math.round(t.latencia_ms / 100) / 10}s
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
