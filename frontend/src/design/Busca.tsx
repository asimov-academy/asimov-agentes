import { useEffect, useId, useRef, useState } from "react";
import { Icone } from "./Icone";

/** A lupa do cabeçalho: clicada, ela abre para o lado e vira um campo.
 *
 *  Uma peça só para as duas buscas do painel, porque para quem usa é o mesmo gesto:
 *
 *  - **filtrar a lista abaixo** (agentes, conversas, canais, contatos): o que se digita corta o que
 *    está na tela, e pronto;
 *  - **escolher uma empresa** (visão geral, oportunidades): com `opcoes`, o que se digita filtra a
 *    lista que abre embaixo do campo, e escolher aplica o filtro da tela. Antes isso era um `select`
 *    e depois um menu com a lista inteira dentro, dois controles diferentes do resto.
 *
 *  Fechada, ela ocupa um botão; aberta, a largura de um campo. A transição é de largura, e quem
 *  pede menos movimento no sistema recebe o campo já aberto.
 */
export function Busca({
  valor,
  aoMudar,
  rotulo,
  placeholder,
  opcoes,
  escolhida,
  aoEscolher,
}: {
  valor: string;
  aoMudar: (texto: string) => void;
  /** O que ela procura, para o leitor de tela: "Buscar agente". */
  rotulo: string;
  placeholder: string;
  /** Com elas, a busca vira escolha: o texto filtra a lista e o clique aplica. */
  opcoes?: { id: string; nome: string }[];
  /** O id escolhido hoje. Vazio, quando `opcoes` aceita, é "todas". */
  escolhida?: string;
  aoEscolher?: (id: string) => void;
}) {
  const [aberta, setAberta] = useState(false);
  const caixa = useRef<HTMLDivElement>(null);
  const campo = useRef<HTMLInputElement>(null);
  const lista = useId();

  useEffect(() => {
    if (aberta) campo.current?.focus();
  }, [aberta]);

  // Com lista aberta o clique fora fecha; sem ela, quem fecha é o `onBlur` do campo.
  useEffect(() => {
    if (!aberta || !opcoes) return;
    const fora = (e: MouseEvent) => {
      if (!caixa.current?.contains(e.target as Node)) setAberta(false);
    };
    document.addEventListener("mousedown", fora);
    return () => document.removeEventListener("mousedown", fora);
  }, [aberta, opcoes]);

  const escolha = opcoes?.find((o) => o.id === escolhida);
  const procurado = valor.trim().toLowerCase();
  const achadas = (opcoes ?? []).filter((o) => o.nome.toLowerCase().includes(procurado));

  function fecha() {
    aoMudar("");
    setAberta(false);
  }

  function escolhe(id: string) {
    aoEscolher?.(id);
    aoMudar("");
    setAberta(false);
  }

  // Escolhida uma empresa, o nome dela fica à vista no lugar do texto digitado: é o filtro que
  // está valendo, e filtro escondido faz a pessoa achar que a tela está incompleta.
  const mostraEscolha = Boolean(escolha) && !aberta;

  return (
    <div ref={caixa} className="relative">
      <div
        className={`flex items-center rounded-md border transition-[width,border-color] duration-200 motion-reduce:transition-none ${
          // Fechada sem escolha ela é só o ícone; com escolha, ganha a moldura dos outros
          // controles do cabeçalho, e não uma só dela.
          aberta
            ? "h-11 w-64 border-ciano bg-surface"
            : mostraEscolha
              ? "h-11 w-auto border-borda"
              : "h-11 w-11 border-transparent"
        }`}
      >
        <button
          onClick={() => (aberta ? campo.current?.focus() : setAberta(true))}
          aria-label={rotulo}
          aria-expanded={aberta}
          title={rotulo}
          className={`flex h-full shrink-0 items-center justify-center rounded-md transition-colors ${
            mostraEscolha ? "gap-2 px-3 text-texto" : "w-11 text-muted hover:text-texto"
          }`}
        >
          {/* O ícone em ciano é o que diz que há um filtro valendo. */}
          <Icone nome="sys-search" tamanho={20} className={mostraEscolha ? "text-ciano" : ""} />
          {mostraEscolha && (
            <span className="max-w-[12rem] truncate text-sm">{escolha?.nome}</span>
          )}
        </button>

        <input
          ref={campo}
          value={valor}
          onChange={(e) => aoMudar(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Escape") fecha();
            if (e.key === "Enter" && opcoes && achadas.length > 0) escolhe(achadas[0].id);
          }}
          // Com lista, quem fecha é o clique fora: sair do campo para clicar num item não pode
          // fechar antes do clique chegar.
          onBlur={() => !opcoes && !valor.trim() && setAberta(false)}
          placeholder={placeholder}
          aria-label={rotulo}
          aria-controls={opcoes ? lista : undefined}
          // Fechada, ela sai da ordem de tabulação: quem navega por teclado chega pelo botão.
          tabIndex={aberta ? 0 : -1}
          className={`min-w-0 bg-transparent pr-2 text-sm text-texto placeholder:text-dim focus:outline-none focus-visible:ring-0 ${
            aberta ? "flex-1" : "pointer-events-none w-0 opacity-0"
          }`}
        />

        {aberta && valor && !opcoes && (
          <button
            onClick={fecha}
            aria-label="Limpar a busca"
            title="Limpar"
            className="flex h-11 w-9 shrink-0 items-center justify-center text-dim transition-colors hover:text-texto"
          >
            <Icone nome="sys-close" tamanho={16} />
          </button>
        )}
      </div>

      {aberta && opcoes && (
        <ul
          id={lista}
          className="absolute right-0 top-full z-30 mt-1 max-h-72 w-64 overflow-y-auto rounded-lg border border-borda bg-panel p-1 shadow-alto"
        >
          {aoEscolher && !procurado && escolhida !== undefined && (
            <Opcao nome="Todas as empresas" marcada={!escolhida} aoIr={() => escolhe("")} />
          )}
          {achadas.map((o) => (
            <Opcao
              key={o.id}
              nome={o.nome}
              marcada={o.id === escolhida}
              aoIr={() => escolhe(o.id)}
            />
          ))}
          {achadas.length === 0 && (
            <li className="px-3 py-2 text-sm text-dim">nenhuma com esse nome</li>
          )}
        </ul>
      )}
    </div>
  );
}

function Opcao({ nome, marcada, aoIr }: { nome: string; marcada: boolean; aoIr: () => void }) {
  return (
    <li>
      <button
        onClick={aoIr}
        aria-current={marcada || undefined}
        className={`flex min-h-11 w-full items-center justify-between gap-2 rounded-md px-3 text-left text-sm transition-colors hover:bg-surface ${
          marcada ? "text-ciano" : "text-muted hover:text-texto"
        }`}
      >
        <span className="truncate">{nome}</span>
        {marcada && <Icone nome="act-check" tamanho={14} />}
      </button>
    </li>
  );
}
