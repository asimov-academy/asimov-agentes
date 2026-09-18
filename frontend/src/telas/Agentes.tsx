import { useCallback, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api, SemSessao, type Agente, type Empresa } from "../api/cliente";
import { Aviso } from "../design/Aviso";
import { Botao } from "../design/Botao";
import { Carregando } from "../design/Carregando";
import { Icone } from "../design/Icone";
import { Marca } from "../design/Marca";
import { Selo } from "../design/Selo";
import { Vazio } from "../design/Vazio";
import { Ficha } from "./agente/Ficha";
import { CANAIS, ROTULO_DO_CANAL } from "./agente/canais";
import { Onboarding } from "./agente/Onboarding";

/** A lista de agentes. O popup abre por cima dela, que fica embaçada atrás: é a regra do operador
 *  para toda configuração de agente.
 *
 *  A lista mostra o mínimo para escolher um agente: a inicial, o nome, onde ele atende e a
 *  situação. Tudo o mais está a um clique, dentro do popup.
 */

const FILTROS = [
  { rotulo: "Todos", valor: undefined },
  { rotulo: "Ativos", valor: true },
  { rotulo: "Inativos", valor: false },
] as const;

export function Agentes({
  empresas,
  empresa,
  aoTrocarEmpresa,
  abrindo,
}: {
  empresas: Empresa[];
  empresa: string;
  aoTrocarEmpresa: (id: string) => void;
  /** `novo` abre o onboarding; um id abre a ficha daquele agente. */
  abrindo?: "novo";
}) {
  const [agentes, setAgentes] = useState<Agente[] | null>(null);
  const [ativo, setAtivo] = useState<boolean | undefined>(undefined);
  const [erro, setErro] = useState("");
  const navega = useNavigate();
  const { id } = useParams();

  const busca = useCallback(() => {
    setErro("");
    api
      .agentes(empresa || undefined, ativo)
      .then(setAgentes)
      .catch((problema) => {
        if (problema instanceof SemSessao) throw problema;
        setErro(problema.message);
      });
  }, [empresa, ativo]);

  useEffect(busca, [busca]);

  return (
    <>
      <header className="flex flex-wrap items-end justify-between gap-6 border-b border-borda pb-6">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight text-texto md:text-5xl">
            Agentes<span className="text-ciano">.</span>
          </h1>
          {/* A contagem só aparece quando há o que contar: sem agente, quem diz isso é o estado
              vazio, e quem está buscando já tem o carregando embaixo. */}
          {agentes !== null && agentes.length > 0 && (
            <p className="mt-2 text-sm text-muted">
              {agentes.length} {agentes.length === 1 ? "agente" : "agentes"}
            </p>
          )}
        </div>

        <div className="flex flex-wrap items-center gap-3">
          {empresas.length > 1 && (
            <select
              value={empresa}
              aria-label="Empresa"
              onChange={(e) => aoTrocarEmpresa(e.target.value)}
              className="rounded-md border border-borda bg-surface px-3 py-2 text-sm text-muted transition-colors hover:text-texto focus:border-ciano focus:outline-none"
            >
              <option value="">Todas as empresas</option>
              {empresas.map((e) => (
                <option key={e.id} value={e.id}>
                  {e.nome}
                </option>
              ))}
            </select>
          )}

          <div className="flex rounded-md border border-borda p-0.5" role="group" aria-label="Situação">
            {FILTROS.map((f) => (
              <button
                key={f.rotulo}
                onClick={() => setAtivo(f.valor)}
                aria-pressed={ativo === f.valor}
                className={`rounded-sm px-3.5 py-1.5 text-xs font-semibold transition-colors ${
                  ativo === f.valor ? "bg-texto text-void" : "text-muted hover:text-texto"
                }`}
              >
                {f.rotulo}
              </button>
            ))}
          </div>

          <Botao tom="acento" pequeno icone="act-add" onClick={() => navega("/agentes/novo")}>
            Criar agente
          </Botao>
        </div>
      </header>

      {erro ? (
        <div className="mt-10">
          <Aviso tom="erro" titulo="não deu para carregar os agentes">
            <p>{erro}</p>
            <div className="mt-4">
              <Botao icone="sys-refresh" pequeno onClick={busca}>
                Tentar de novo
              </Botao>
            </div>
          </Aviso>
        </div>
      ) : agentes === null ? (
        <div className="mt-16">
          <Carregando tipo="pontos" o_que="buscando os agentes" />
        </div>
      ) : agentes.length === 0 ? (
        <div className="mt-16">
          <Vazio titulo="nenhum agente ainda" icone="nav-team">
            Crie o primeiro e converse com ele antes de conectar a um canal.
          </Vazio>
        </div>
      ) : (
        <ul className="mt-8 flex flex-col gap-1">
          {agentes.map((a) => {
            const marca = CANAIS[a.canal]?.marca;
            return (
              <li key={a.id}>
                <button
                  onClick={() => navega(`/agentes/${a.id}`)}
                  className="flex w-full items-center gap-4 rounded-md px-3 py-3 text-left transition-colors hover:bg-surface"
                >
                  <span
                    className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-md border text-sm font-semibold ${
                      a.ativo ? "border-ciano/40 text-ciano" : "border-dim text-dim"
                    }`}
                  >
                    {a.nome.slice(0, 1).toUpperCase()}
                  </span>

                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-base text-texto">{a.nome}</span>
                    <span className="mt-0.5 flex items-center gap-1.5 text-sm text-muted">
                      {marca && <Marca nome={marca} tamanho={14} apagada={!a.ativo} />}
                      <span className="truncate">
                        {ROTULO_DO_CANAL(a.canal)}
                        {empresa ? "" : `, em ${a.empresa}`}
                      </span>
                    </span>
                  </span>

                  {!a.ativo && <Selo>inativo</Selo>}
                  <Icone nome="sys-chevron" className="text-dim" />
                </button>
              </li>
            );
          })}
        </ul>
      )}

      {abrindo === "novo" && (
        <Onboarding
          empresas={empresas}
          aoFechar={() => navega("/agentes")}
          aoCriar={(agente) => {
            busca();
            navega(`/agentes/${agente.id}`);
          }}
        />
      )}

      {id && id !== "novo" && (
        <Ficha
          agenteId={id}
          aoFechar={() => navega("/agentes")}
          aoMudar={busca}
        />
      )}
    </>
  );
}
