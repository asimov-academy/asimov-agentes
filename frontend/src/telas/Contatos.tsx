import { useCallback, useEffect, useState } from "react";
import {
  api,
  SemSessao,
  type Contato,
  type ContatoAberto,
  type Empresa,
} from "../api/cliente";
import { Aviso } from "../design/Aviso";
import { Campo } from "../design/Campo";
import { Carregando } from "../design/Carregando";
import { Modal } from "../design/Modal";
import { Selo } from "../design/Selo";
import { Vazio } from "../design/Vazio";
import { ROTULO_DO_CANAL } from "./agente/canais";

/** A tela de Contatos: busca por nome ou telefone, e a ficha com as conversas da pessoa.
 *
 *  Sem exportação em massa, de propósito: a lista tem teto e só serve para achar uma pessoa.
 */

const data = (iso: string) => new Date(iso).toLocaleDateString("pt-BR");

export function Contatos({
  empresas,
  empresa,
  aoTrocarEmpresa,
}: {
  empresas: Empresa[];
  empresa: string;
  aoTrocarEmpresa: (id: string) => void;
}) {
  const [busca, setBusca] = useState("");
  const [contatos, setContatos] = useState<Contato[] | null>(null);
  const [aberto, setAberto] = useState<ContatoAberto | null>(null);
  const [erro, setErro] = useState("");

  const procura = useCallback(() => {
    setErro("");
    api
      .contatos(busca, empresa || undefined)
      .then(setContatos)
      .catch((problema) => {
        if (problema instanceof SemSessao) throw problema;
        setErro(problema.message);
      });
  }, [busca, empresa]);

  // Espera a digitação parar: cada tecla não vira uma consulta.
  useEffect(() => {
    const t = setTimeout(procura, busca ? 300 : 0);
    return () => clearTimeout(t);
  }, [procura, busca]);

  return (
    <>
      <header className="flex flex-wrap items-end justify-between gap-6 border-b border-borda pb-6">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight text-texto md:text-5xl">
            Contatos<span className="text-lime">.</span>
          </h1>
          <p className="mt-2 text-sm text-muted">Quem já conversou com algum agente.</p>
        </div>

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
      </header>

      <div className="mt-8 max-w-md">
        <Campo
          rotulo="Procurar"
          icone="sys-search"
          placeholder="nome ou telefone"
          value={busca}
          onChange={(e) => setBusca(e.target.value)}
        />
      </div>

      {erro ? (
        <div className="mt-8">
          <Aviso tom="erro" titulo="a busca não voltou">
            {erro}
          </Aviso>
        </div>
      ) : contatos === null ? (
        <div className="mt-12">
          <Carregando tipo="pontos" o_que="procurando" />
        </div>
      ) : contatos.length === 0 ? (
        <div className="mt-12">
          <Vazio titulo={busca ? "ninguém com esse nome ou número" : "nenhum contato ainda"} icone="comm-mention">
            {busca
              ? "Tente só o começo do nome, ou o número sem pontuação."
              : "Cada pessoa que escrever para um agente aparece aqui."}
          </Vazio>
        </div>
      ) : (
        <ul className="mt-8 border-t border-borda">
          {contatos.map((c) => (
            <li key={c.id}>
              <button
                onClick={() => api.contato(c.id).then(setAberto)}
                className="flex w-full items-center justify-between gap-4 border-b border-borda py-4 text-left transition-colors hover:bg-surface"
              >
                <span className="min-w-0">
                  <span className="block truncate text-base text-texto">
                    {c.nome ?? "sem nome"}
                  </span>
                  <span className="mt-0.5 block truncate text-sm text-muted">
                    {c.telefone ?? "sem telefone"}, fala com {c.agente}
                  </span>
                </span>
                <span className="shrink-0 font-mono text-xs text-dim">
                  {data(c.ultima_mensagem_em)}
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}

      {aberto && (
        <Modal
          titulo={aberto.nome ?? "Contato"}
          subtitulo={`${aberto.telefone ?? "sem telefone"}, em ${aberto.empresa}`}
          aoFechar={() => setAberto(null)}
          largura="max-w-2xl"
        >
          <dl className="flex flex-col divide-y divide-borda border-y border-borda">
            <Linha rotulo="Fala com">{aberto.agente}</Linha>
            <Linha rotulo="Primeira mensagem">{data(aberto.criado_em)}</Linha>
            <Linha rotulo="Última mensagem">{data(aberto.ultima_mensagem_em)}</Linha>
          </dl>

          <h3 className="mt-8 text-lg font-semibold text-texto">Conversas</h3>
          {aberto.conversas.length === 0 ? (
            <p className="mt-2 text-sm text-dim">Nenhuma conversa guardada.</p>
          ) : (
            <ul className="mt-3 border-t border-borda">
              {aberto.conversas.map((c) => (
                <li
                  key={c.id}
                  className="flex items-center justify-between gap-4 border-b border-borda py-3"
                >
                  <span className="text-sm text-texto">{ROTULO_DO_CANAL(c.canal)}</span>
                  <span className="flex items-center gap-3">
                    {c.status === "humano" && <Selo tom="atencao">com gente</Selo>}
                    <span className="font-mono text-xs text-dim">{data(c.atualizado_em)}</span>
                  </span>
                </li>
              ))}
            </ul>
          )}
        </Modal>
      )}
    </>
  );
}

function Linha({ rotulo, children }: { rotulo: string; children: React.ReactNode }) {
  return (
    <div className="flex items-baseline justify-between gap-6 py-3">
      <dt className="rotulo">{rotulo}</dt>
      <dd className="text-right text-sm text-texto">{children}</dd>
    </div>
  );
}
