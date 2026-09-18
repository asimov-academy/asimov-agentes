import { useCallback, useEffect, useState } from "react";
import {
  api,
  ErroDaApi,
  SemSessao,
  type CorDeEtiqueta,
  type Empresa,
  type EtiquetaDoFunil,
  type Funil as Quadro,
  type OportunidadeDoFunil,
} from "../api/cliente";
import { Aviso } from "../design/Aviso";
import { Botao } from "../design/Botao";
import { Cabecalho } from "../design/Cabecalho";
import { Campo } from "../design/Campo";
import { Carregando } from "../design/Carregando";
import { Icone } from "../design/Icone";
import { Modal } from "../design/Modal";
import { Selo } from "../design/Selo";
import { Vazio } from "../design/Vazio";

/** O kanban de oportunidades de uma empresa.
 *
 *  Arrastar é com o arrasto nativo do navegador (`draggable` e `dataTransfer`), não com biblioteca:
 *  a regra do projeto é que nada de interface vem de fora. Soltar o cartão manda um PATCH e o
 *  quadro é relido; enquanto o servidor não responde, o cartão já aparece na coluna nova, senão a
 *  mão chega antes da rede e parece que o arrasto não pegou.
 */
const CORES: Record<CorDeEtiqueta, string> = {
  ciano: "border-ciano/40 text-ciano",
  ok: "border-ok/40 text-ok",
  atencao: "border-atencao/40 text-atencao",
  perigo: "border-perigo/40 text-perigo",
  muted: "border-borda text-muted",
};

const CORES_DISPONIVEIS: CorDeEtiqueta[] = ["ciano", "ok", "atencao", "perigo", "muted"];

function dinheiro(valor: string): string {
  const numero = Number(valor);
  if (!Number.isFinite(numero) || numero === 0) return "";
  return numero.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

export function Funil({
  empresas,
  empresa,
  aoTrocarEmpresa,
}: {
  empresas: Empresa[];
  empresa: string;
  aoTrocarEmpresa: (id: string) => void;
}) {
  // O funil é de uma empresa: sem ela escolhida, a primeira da lista serve de padrão.
  const escolhida = empresa || empresas[0]?.id || "";
  const [quadro, setQuadro] = useState<Quadro | null>(null);
  const [erro, setErro] = useState("");
  const [arrastando, setArrastando] = useState("");
  const [sobre, setSobre] = useState("");
  const [abrindo, setAbrindo] = useState<OportunidadeDoFunil | "nova" | null>(null);
  const [etiquetas, setEtiquetas] = useState(false);

  const busca = useCallback(() => {
    if (!escolhida) return;
    setErro("");
    api
      .funil(escolhida)
      .then(setQuadro)
      .catch((problema) => {
        if (problema instanceof SemSessao) throw problema;
        setErro(problema.message);
      });
  }, [escolhida]);

  useEffect(busca, [busca]);

  async function move(oportunidade: OportunidadeDoFunil, etapaId: string) {
    if (oportunidade.etapa_id === etapaId) return;
    // Mexe na tela primeiro: a mão chega antes da rede, e o cartão voltando para a coluna antiga
    // por meio segundo parece que o arrasto não pegou.
    setQuadro((antes) =>
      antes
        ? {
            ...antes,
            oportunidades: antes.oportunidades.map((o) =>
              o.id === oportunidade.id ? { ...o, etapa_id: etapaId } : o,
            ),
          }
        : antes,
    );
    try {
      await api.editaOportunidade(escolhida, oportunidade.id, { etapa_id: etapaId });
    } catch (problema) {
      setErro(problema instanceof ErroDaApi ? problema.message : String(problema));
    } finally {
      busca();
    }
  }

  if (empresas.length === 0) {
    return (
      <>
        <Cabecalho titulo="Oportunidades" contexto="O funil de cada empresa." />
        <div className="mt-10">
          <Vazio titulo="nenhuma empresa ainda" icone="nav-reports">
            Crie um agente e a empresa dele nasce junto.
          </Vazio>
        </div>
      </>
    );
  }

  return (
    <>
      <Cabecalho
        titulo="Oportunidades"
        contexto={quadro ? `${quadro.oportunidades.length} no funil` : undefined}
        acoes={
          <>
            {empresas.length > 1 && (
              <select
                value={escolhida}
                aria-label="Empresa"
                onChange={(e) => aoTrocarEmpresa(e.target.value)}
                className="rounded-md border border-borda bg-surface px-3 py-2 text-xs text-muted transition-colors hover:text-texto focus:border-ciano focus:outline-none"
              >
                {empresas.map((e) => (
                  <option key={e.id} value={e.id}>
                    {e.nome}
                  </option>
                ))}
              </select>
            )}
            <Botao pequeno icone="cont-doc" onClick={() => setEtiquetas(true)}>
              Etiquetas
            </Botao>
            <Botao tom="acento" pequeno icone="act-add" onClick={() => setAbrindo("nova")}>
              Nova oportunidade
            </Botao>
          </>
        }
      />

      {erro ? (
        <div className="mt-10">
          <Aviso tom="erro" titulo="não deu para carregar o funil">
            <p>{erro}</p>
            <div className="mt-4">
              <Botao icone="sys-refresh" pequeno onClick={busca}>
                Tentar de novo
              </Botao>
            </div>
          </Aviso>
        </div>
      ) : quadro === null ? (
        <div className="mt-16">
          <Carregando tipo="pontos" o_que="montando o funil" />
        </div>
      ) : (
        <div className="mt-6 flex gap-3 overflow-x-auto pb-4">
          {quadro.etapas.map((etapa) => {
            const cartoes = quadro.oportunidades
              .filter((o) => o.etapa_id === etapa.id)
              .sort((a, b) => a.ordem - b.ordem);
            return (
              <section
                key={etapa.id}
                onDragOver={(e) => {
                  e.preventDefault();
                  setSobre(etapa.id);
                }}
                onDragLeave={() => setSobre((antes) => (antes === etapa.id ? "" : antes))}
                onDrop={(e) => {
                  e.preventDefault();
                  setSobre("");
                  const cartao = quadro.oportunidades.find((o) => o.id === arrastando);
                  if (cartao) void move(cartao, etapa.id);
                  setArrastando("");
                }}
                className={`flex w-72 shrink-0 flex-col rounded-lg border bg-surface transition-colors ${
                  sobre === etapa.id ? "border-ciano" : "border-borda"
                }`}
              >
                <header className="flex items-baseline justify-between gap-2 border-b border-borda px-4 py-3">
                  <span className="flex min-w-0 items-baseline gap-2">
                    <span className="truncate text-sm font-medium text-texto">{etapa.nome}</span>
                    <span className="shrink-0 text-xs text-dim">{cartoes.length}</span>
                  </span>
                  {dinheiro(etapa.total) && (
                    <span className="tecnico shrink-0 text-xs text-muted">{dinheiro(etapa.total)}</span>
                  )}
                </header>

                <ul className="flex min-h-[6rem] flex-1 flex-col gap-2 p-2">
                  {cartoes.map((o) => (
                    <li key={o.id}>
                      <button
                        draggable
                        onDragStart={() => setArrastando(o.id)}
                        onDragEnd={() => setArrastando("")}
                        onClick={() => setAbrindo(o)}
                        className={`w-full cursor-grab rounded-md border border-borda bg-panel p-3 text-left transition-colors hover:border-dim active:cursor-grabbing ${
                          arrastando === o.id ? "opacity-40" : ""
                        }`}
                      >
                        <span className="block text-sm leading-snug text-texto">{o.titulo}</span>
                        {o.contato && (
                          <span className="mt-1 block truncate text-xs text-muted">{o.contato}</span>
                        )}
                        {dinheiro(o.valor) && (
                          <span className="tecnico mt-1 block text-xs text-muted">{dinheiro(o.valor)}</span>
                        )}
                        {o.etiquetas.length > 0 && (
                          <span className="mt-2 flex flex-wrap gap-1">
                            {o.etiquetas.map((id) => {
                              const etiqueta = quadro.etiquetas.find((e) => e.id === id);
                              if (!etiqueta) return null;
                              return (
                                <span
                                  key={id}
                                  className={`rounded-full border px-2 py-px text-[0.625rem] ${CORES[etiqueta.cor]}`}
                                >
                                  {etiqueta.nome}
                                </span>
                              );
                            })}
                          </span>
                        )}
                      </button>
                    </li>
                  ))}

                  {cartoes.length === 0 && (
                    <li className="flex flex-1 items-center justify-center px-2 py-6 text-center text-xs text-dim">
                      arraste um cartão para cá
                    </li>
                  )}
                </ul>
              </section>
            );
          })}

          <ColunaNova empresa={escolhida} aoCriar={busca} aoFalhar={setErro} />
        </div>
      )}

      {abrindo && quadro && (
        <Ficha
          empresa={escolhida}
          quadro={quadro}
          oportunidade={abrindo === "nova" ? null : abrindo}
          aoFechar={() => setAbrindo(null)}
          aoSalvar={() => {
            setAbrindo(null);
            busca();
          }}
        />
      )}

      {etiquetas && quadro && (
        <Etiquetas
          empresa={escolhida}
          etiquetas={quadro.etiquetas}
          aoFechar={() => setEtiquetas(false)}
          aoMudar={busca}
        />
      )}
    </>
  );
}

/** A coluna que cria coluna. Fica no fim do quadro, que é onde a mão procura por ela. */
function ColunaNova({
  empresa,
  aoCriar,
  aoFalhar,
}: {
  empresa: string;
  aoCriar: () => void;
  aoFalhar: (erro: string) => void;
}) {
  const [nome, setNome] = useState("");
  const [aberto, setAberto] = useState(false);

  async function cria() {
    if (!nome.trim()) return;
    try {
      await api.criaEtapa(empresa, nome.trim());
      setNome("");
      setAberto(false);
      aoCriar();
    } catch (problema) {
      aoFalhar(problema instanceof ErroDaApi ? problema.message : String(problema));
    }
  }

  if (!aberto) {
    return (
      <button
        onClick={() => setAberto(true)}
        className="flex w-56 shrink-0 items-center justify-center gap-2 rounded-lg border border-dashed border-borda p-4 text-sm text-dim transition-colors hover:border-dim hover:text-muted"
      >
        <Icone nome="act-add" tamanho={16} />
        Nova coluna
      </button>
    );
  }

  return (
    <div className="flex w-72 shrink-0 flex-col gap-3 rounded-lg border border-borda bg-surface p-4">
      <Campo
        rotulo="Nome da coluna"
        autoFocus
        value={nome}
        onChange={(e) => setNome(e.target.value)}
        onKeyDown={(e) => e.key === "Enter" && void cria()}
      />
      <div className="flex gap-2">
        <Botao pequeno tom="acento" onClick={cria}>
          Criar
        </Botao>
        <Botao pequeno onClick={() => setAberto(false)}>
          Cancelar
        </Botao>
      </div>
    </div>
  );
}

/** O popup do cartão: criar, editar, marcar etiqueta e remover. */
function Ficha({
  empresa,
  quadro,
  oportunidade,
  aoFechar,
  aoSalvar,
}: {
  empresa: string;
  quadro: Quadro;
  oportunidade: OportunidadeDoFunil | null;
  aoFechar: () => void;
  aoSalvar: () => void;
}) {
  const [titulo, setTitulo] = useState(oportunidade?.titulo ?? "");
  const [valor, setValor] = useState(oportunidade?.valor ?? "");
  const [nota, setNota] = useState(oportunidade?.nota ?? "");
  const [etapaId, setEtapaId] = useState(oportunidade?.etapa_id ?? quadro.etapas[0]?.id ?? "");
  const [marcadas, setMarcadas] = useState<string[]>(oportunidade?.etiquetas ?? []);
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro] = useState("");

  async function salva() {
    setErro("");
    setSalvando(true);
    try {
      const dados = {
        titulo: titulo.trim(),
        valor: valor.trim() || "0",
        nota,
        etapa_id: etapaId,
        etiquetas: marcadas,
      };
      if (oportunidade) await api.editaOportunidade(empresa, oportunidade.id, dados);
      else await api.criaOportunidade(empresa, dados);
      aoSalvar();
    } catch (problema) {
      setErro(problema instanceof ErroDaApi ? problema.message : String(problema));
    } finally {
      setSalvando(false);
    }
  }

  async function remove() {
    if (!oportunidade) return;
    setSalvando(true);
    try {
      await api.apagaOportunidade(empresa, oportunidade.id);
      aoSalvar();
    } catch (problema) {
      setErro(problema instanceof ErroDaApi ? problema.message : String(problema));
    } finally {
      setSalvando(false);
    }
  }

  return (
    <Modal
      titulo={oportunidade ? oportunidade.titulo : "Nova oportunidade"}
      subtitulo={oportunidade?.contato ?? undefined}
      aoFechar={aoFechar}
      largura="max-w-2xl"
      rodape={
        <>
          {oportunidade && (
            <Botao tom="perigo" pequeno icone="act-delete" ocupado={salvando} onClick={remove}>
              Remover
            </Botao>
          )}
          <Botao
            tom="solido"
            pequeno
            icone="act-save"
            ocupado={salvando}
            disabled={!titulo.trim()}
            onClick={salva}
          >
            Salvar
          </Botao>
        </>
      }
    >
      {erro && (
        <div className="mb-5">
          <Aviso tom="erro" titulo="não deu para salvar">
            <p>{erro}</p>
          </Aviso>
        </div>
      )}

      <div className="grid gap-4 sm:grid-cols-2">
        <Campo
          rotulo="Título"
          autoFocus
          value={titulo}
          onChange={(e) => setTitulo(e.target.value)}
          placeholder="o que está em jogo"
        />
        <Campo
          rotulo="Valor"
          value={valor}
          onChange={(e) => setValor(e.target.value)}
          placeholder="0,00"
        />
      </div>

      <label className="mt-4 block">
        <span className="rotulo">Coluna</span>
        <select
          value={etapaId}
          onChange={(e) => setEtapaId(e.target.value)}
          className="mt-2 w-full rounded-md border border-borda bg-surface px-3 py-2 text-sm text-texto focus:border-ciano focus:outline-none"
        >
          {quadro.etapas.map((e) => (
            <option key={e.id} value={e.id}>
              {e.nome}
            </option>
          ))}
        </select>
      </label>

      {quadro.etiquetas.length > 0 && (
        <div className="mt-5">
          <p className="rotulo">Etiquetas</p>
          <div className="mt-2 flex flex-wrap gap-2">
            {quadro.etiquetas.map((e) => {
              const marcada = marcadas.includes(e.id);
              return (
                <button
                  key={e.id}
                  aria-pressed={marcada}
                  onClick={() =>
                    setMarcadas((antes) =>
                      marcada ? antes.filter((i) => i !== e.id) : [...antes, e.id],
                    )
                  }
                  className={`rounded-full border px-3 py-1 text-xs transition-colors ${
                    marcada ? CORES[e.cor] : "border-borda text-dim hover:text-muted"
                  }`}
                >
                  {e.nome}
                </button>
              );
            })}
          </div>
        </div>
      )}

      <label className="mt-5 block">
        <span className="rotulo">Nota</span>
        <textarea
          rows={4}
          value={nota}
          onChange={(e) => setNota(e.target.value)}
          placeholder="o que ficou combinado"
          className="mt-2 w-full rounded-md border border-borda bg-surface px-3 py-2 text-sm text-texto transition-colors placeholder:text-dim focus:border-ciano focus:outline-none focus:ring-1 focus:ring-ciano"
        />
      </label>
    </Modal>
  );
}

/** O popup das etiquetas: criar, ver e remover. Apagar uma tira ela dos cartões junto. */
function Etiquetas({
  empresa,
  etiquetas,
  aoFechar,
  aoMudar,
}: {
  empresa: string;
  etiquetas: EtiquetaDoFunil[];
  aoFechar: () => void;
  aoMudar: () => void;
}) {
  const [nome, setNome] = useState("");
  const [cor, setCor] = useState<CorDeEtiqueta>("ciano");
  const [erro, setErro] = useState("");
  const [ocupado, setOcupado] = useState(false);

  async function cria() {
    if (!nome.trim()) return;
    setErro("");
    setOcupado(true);
    try {
      await api.criaEtiqueta(empresa, nome.trim(), cor);
      setNome("");
      aoMudar();
    } catch (problema) {
      setErro(problema instanceof ErroDaApi ? problema.message : String(problema));
    } finally {
      setOcupado(false);
    }
  }

  async function remove(id: string) {
    setErro("");
    try {
      await api.apagaEtiqueta(empresa, id);
      aoMudar();
    } catch (problema) {
      setErro(problema instanceof ErroDaApi ? problema.message : String(problema));
    }
  }

  return (
    <Modal
      titulo="Etiquetas"
      subtitulo="Marcações do funil desta empresa"
      aoFechar={aoFechar}
      largura="max-w-xl"
    >
      {erro && (
        <div className="mb-5">
          <Aviso tom="erro" titulo="não deu">
            <p>{erro}</p>
          </Aviso>
        </div>
      )}

      <div className="flex flex-wrap items-end gap-3">
        <div className="min-w-[12rem] flex-1">
          <Campo
            rotulo="Nova etiqueta"
            value={nome}
            onChange={(e) => setNome(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && void cria()}
            placeholder="Urgente"
          />
        </div>
        <div className="flex gap-1.5 pb-1">
          {CORES_DISPONIVEIS.map((c) => (
            <button
              key={c}
              aria-label={`Cor ${c}`}
              aria-pressed={cor === c}
              onClick={() => setCor(c)}
              className={`h-7 w-7 rounded-full border transition-colors ${CORES[c]} ${
                cor === c ? "ring-1 ring-ciano" : ""
              }`}
            >
              <span className="sr-only">{c}</span>
            </button>
          ))}
        </div>
        <Botao pequeno tom="acento" ocupado={ocupado} disabled={!nome.trim()} onClick={cria}>
          Criar
        </Botao>
      </div>

      <ul className="mt-6 flex flex-col gap-1">
        {etiquetas.map((e) => (
          <li
            key={e.id}
            className="flex items-center justify-between gap-3 rounded-md border border-borda px-3 py-2"
          >
            <Selo tom={e.cor === "muted" ? "neutro" : e.cor === "ciano" ? "acento" : e.cor}>
              {e.nome}
            </Selo>
            <button
              onClick={() => remove(e.id)}
              aria-label={`Remover ${e.nome}`}
              className="rounded-md p-1.5 text-dim transition-colors hover:bg-panel hover:text-perigo"
            >
              <Icone nome="act-delete" tamanho={16} />
            </button>
          </li>
        ))}
        {etiquetas.length === 0 && (
          <li className="py-4 text-center text-sm text-dim">nenhuma etiqueta ainda</li>
        )}
      </ul>
    </Modal>
  );
}
