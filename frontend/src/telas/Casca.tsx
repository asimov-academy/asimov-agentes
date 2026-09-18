import { useEffect, useState, type ReactNode } from "react";
import { NavLink, useLocation } from "react-router-dom";
import type { Eu } from "../api/cliente";
import { Icone } from "../design/Icone";
import type { ICONES } from "../design/icones";

/** Itens do menu. Ordem e rotas vêm de spec/frontend.md, seção 4; os ícones saem do sprite do
 *  design system, nunca de biblioteca de fora. */
const ITENS: { para: string; texto: string; icone: keyof typeof ICONES; fim?: boolean; embreve?: boolean }[] = [
  { para: "/", texto: "Visão geral", icone: "nav-dashboard", fim: true },
  { para: "/agentes", texto: "Agentes", icone: "nav-team" },
  { para: "/canais", texto: "Canais", icone: "cont-link" },
  { para: "/chat", texto: "Chat", icone: "comm-chat" },
  { para: "/contatos", texto: "Contatos", icone: "comm-mention" },
  { para: "/conhecimento", texto: "Conhecimento", icone: "cont-doc", embreve: true },
];

const CORES_DA_SITUACAO = {
  ok: "bg-ok",
  atencao: "bg-atencao",
  perigo: "bg-perigo",
} as const;

export type Situacao = { cor: keyof typeof CORES_DA_SITUACAO; texto: string };

export function Casca({
  eu,
  situacao,
  children,
}: {
  eu: Eu | null;
  situacao: Situacao | null;
  children: ReactNode;
}) {
  const [recolhido, setRecolhido] = useState(false);
  const [gaveta, setGaveta] = useState(false);
  const local = useLocation();

  // No celular o menu é gaveta: navegar fecha, e Esc fecha sem precisar acertar o fundo.
  useEffect(() => setGaveta(false), [local.pathname]);
  useEffect(() => {
    if (!gaveta) return;
    const tecla = (e: KeyboardEvent) => e.key === "Escape" && setGaveta(false);
    document.addEventListener("keydown", tecla);
    return () => document.removeEventListener("keydown", tecla);
  }, [gaveta]);

  return (
    // A página não rola: quem rola é o conteúdo da direita. É o que deixa o menu parado de verdade
    // em vez de grudado (`sticky` ainda participa da rolagem da página). `h-dvh` em vez de
    // `h-screen` porque no celular a barra do navegador some e volta, e `100vh` não acompanha.
    <div className="flex h-dvh overflow-hidden">
      {/* Fundo da gaveta. Só existe no celular, e fechar por ele é o gesto que a pessoa espera. */}
      {gaveta && (
        <button
          aria-label="Fechar o menu"
          onClick={() => setGaveta(false)}
          className="fixed inset-0 z-30 bg-void/80 md:hidden"
        />
      )}

      <aside
        className={`fixed inset-y-0 left-0 z-40 flex shrink-0 flex-col justify-between border-r border-borda bg-panel transition-all md:static md:h-full md:translate-x-0 ${
          gaveta ? "translate-x-0" : "-translate-x-full"
        } ${recolhido ? "w-16" : "w-60"}`}
      >
        <div className="min-h-0 flex-1 overflow-y-auto">
          <div className="flex items-center gap-3 border-b border-borda px-5 py-5">
            <span className="flex h-7 w-7 shrink-0 items-center justify-center bg-ciano font-mono text-sm font-bold text-void">
              A
            </span>
            {!recolhido && (
              <span className="font-mono text-sm tracking-[0.15em] text-texto">ASIMOV</span>
            )}
            <button
              onClick={() => setGaveta(false)}
              aria-label="Fechar o menu"
              className="ml-auto text-muted hover:text-texto md:hidden"
            >
              <Icone nome="sys-close" tamanho={18} />
            </button>
          </div>

          <nav className="p-3">
            {ITENS.map((item) =>
              item.embreve ? (
                <span
                  key={item.para}
                  aria-disabled="true"
                  title={recolhido ? `${item.texto} (em breve)` : undefined}
                  className="flex cursor-not-allowed items-center gap-3 px-3 py-2 text-sm text-dim"
                >
                  <Icone nome={item.icone} />
                  {!recolhido && (
                    <>
                      <span className="flex-1">{item.texto}</span>
                      <span className="rotulo text-[0.5625rem]">em breve</span>
                    </>
                  )}
                </span>
              ) : (
                <NavLink
                  key={item.para}
                  to={item.para}
                  end={item.fim}
                  title={recolhido ? item.texto : undefined}
                  className={({ isActive }) =>
                    `flex items-center gap-3 border-l-2 px-3 py-2 text-sm transition-colors ${
                      isActive
                        ? "border-l-ciano bg-surface text-ciano"
                        : "border-l-transparent text-muted hover:text-texto"
                    }`
                  }
                >
                  <Icone nome={item.icone} />
                  {!recolhido && <span>{item.texto}</span>}
                </NavLink>
              ),
            )}
          </nav>
        </div>

        <div className="border-t border-borda p-3">
          {/* A situação da plataforma mora aqui, junto do operador e do sair: é informação da
              instalação, não de uma tela. Recolhido, sobra o ponto colorido. */}
          {situacao && (
            <div
              className="flex items-center gap-3 px-2 py-2"
              title={situacao.texto}
              aria-label={`Situação da plataforma: ${situacao.texto}`}
            >
              <span
                className={`h-2 w-2 shrink-0 ${CORES_DA_SITUACAO[situacao.cor]}`}
                aria-hidden="true"
              />
              {!recolhido && (
                <span className="font-mono text-xs leading-tight text-muted">{situacao.texto}</span>
              )}
            </div>
          )}

          <button
            onClick={() => setRecolhido((antes) => !antes)}
            aria-label={recolhido ? "Abrir o menu" : "Recolher o menu"}
            className="hidden w-full items-center gap-3 px-2 py-2 text-muted transition-colors hover:text-texto md:flex"
          >
            <Icone nome={recolhido ? "sys-zoomin" : "sys-zoomout"} />
            {!recolhido && <span className="rotulo">recolher</span>}
          </button>

          {!recolhido && (
            <div className="px-2 pt-3">
              <p className="rotulo">operador</p>
              <p className="mt-1 truncate font-mono text-xs text-muted">
                {eu?.instalacao.subdominio_app || eu?.instalacao.subdominio_bot || "…"}
              </p>
            </div>
          )}
          <form method="post" action="/painel/sair" className="mt-3 px-2">
            <button
              type="submit"
              title="Sair"
              className="flex w-full items-center gap-2 border border-borda px-3 py-1.5 font-mono text-xs uppercase tracking-[0.15em] text-muted transition-colors hover:border-perigo hover:text-perigo"
            >
              <Icone nome="act-cancel" tamanho={14} />
              {!recolhido && "Sair"}
            </button>
          </form>
        </div>
      </aside>

      {/* Sem barra do topo. Ela carregava uma busca desligada e um ponto de situação, e ocupava
          uma faixa inteira da tela para isso. A busca nasce na tela de Agentes, onde ela vale, e a
          situação foi para o rodapé do menu. No celular sobra só o abridor da gaveta, solto sobre
          o conteúdo, com o canto marcado do botão fantasma do design system. */}
      {!gaveta && (
        <button
          onClick={() => setGaveta(true)}
          className="fixed left-4 top-4 z-30 flex items-center gap-2 border border-texto/20 bg-panel px-3 py-1.5 font-mono text-xs uppercase tracking-[0.15em] text-texto transition-colors hover:border-texto/40 md:hidden"
        >
          <Icone nome="nav-dashboard" tamanho={14} />
          Menu
        </button>
      )}

      <main className="min-w-0 flex-1 overflow-y-auto p-4 pt-16 md:p-10">{children}</main>
    </div>
  );
}
