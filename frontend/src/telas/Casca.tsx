import { useEffect, useState, type ReactNode } from "react";
import { NavLink, useLocation } from "react-router-dom";
import type { Eu } from "../api/cliente";
import { Icone } from "../design/Icone";
import type { ICONES } from "../design/icones";

/** O menu, em dois grupos.
 *
 *  Os seis itens eram uma lista corrida, e o operador tinha de ler todos para achar o que queria.
 *  Agora "Operação" é o que se acompanha todo dia e "Atendimento" é onde se lê conversa. O grupo
 *  some quando o menu está recolhido, que é quando o ícone já é a única pista.
 *
 *  **Conhecimento não é item de menu.** A base é de cada agente, e mora na aba Treinamento da ficha
 *  dele: uma tela geral de conhecimento prometia uma base da instalação, que não existe.
 */
type Item = { para: string; texto: string; icone: keyof typeof ICONES; fim?: boolean; embreve?: boolean };

const GRUPOS: { titulo: string; itens: Item[] }[] = [
  {
    titulo: "Operação",
    itens: [
      { para: "/", texto: "Visão geral", icone: "nav-dashboard", fim: true },
      { para: "/agentes", texto: "Agentes", icone: "nav-team" },
      { para: "/canais", texto: "Canais", icone: "cont-link" },
      { para: "/oportunidades", texto: "Oportunidades", icone: "nav-reports" },
    ],
  },
  {
    titulo: "Atendimento",
    itens: [
      { para: "/chat", texto: "Conversas", icone: "comm-chat" },
      { para: "/contatos", texto: "Contatos", icone: "nav-user" },
    ],
  },
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
  copiloto,
  copilotoAberto,
  aoAbrirCopiloto,
}: {
  eu: Eu | null;
  situacao: Situacao | null;
  children: ReactNode;
  /** A coluna da direita, quando aberta. Mora aqui porque divide a largura com o conteúdo. */
  copiloto?: ReactNode;
  copilotoAberto?: boolean;
  aoAbrirCopiloto?: () => void;
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

  const endereco = eu?.instalacao.subdominio_app || eu?.instalacao.subdominio_bot || "…";
  const nomeDoEspaco = eu?.espaco?.nome?.trim() || "ASIMOV";
  const sigla = eu?.espaco?.sigla?.trim() || nomeDoEspaco.slice(0, 1).toUpperCase();
  const quemOpera = eu?.operador?.nome?.trim() || "Operador";

  return (
    // A página não rola: quem rola é o conteúdo da direita. É o que deixa o menu parado de verdade
    // em vez de grudado (`sticky` ainda participa da rolagem da página). `h-dvh` em vez de
    // `h-screen` porque no celular a barra do navegador some e volta, e `100vh` não acompanha.
    <div className="flex h-dvh overflow-hidden bg-void">
      {/* Fundo da gaveta. Só existe no celular, e fechar por ele é o gesto que a pessoa espera. */}
      {gaveta && (
        <button
          aria-label="Fechar o menu"
          onClick={() => setGaveta(false)}
          className="fixed inset-0 z-30 bg-void/80 backdrop-blur-sm md:hidden"
        />
      )}

      <aside
        className={`fixed inset-y-0 left-0 z-40 flex shrink-0 flex-col border-r border-borda bg-panel transition-all md:relative md:z-30 md:h-full md:translate-x-0 ${
          gaveta ? "translate-x-0 shadow-alto" : "-translate-x-full"
        } ${recolhido ? "w-[4.5rem]" : "w-64"}`}
      >
        {/* Recolhido, a faixa é estreita demais para a marca e o botão lado a lado: eles ficavam
            apertados e fora do eixo dos ícones. Sobra a marca, centrada no mesmo eixo, e quem abre
            o menu é o botão que flutua na borda, que não disputa largura nenhuma. */}
        <div className={`flex items-center gap-2.5 px-3 py-4 ${recolhido ? "justify-center" : ""}`}>
          <span
            className="relative flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-ciano text-sm font-bold text-void"
            title={situacao ? `Situação da instalação: ${situacao.texto}` : undefined}
          >
            {sigla}
            {situacao && (
              <span
                aria-hidden="true"
                className={`absolute -bottom-0.5 -right-0.5 h-2.5 w-2.5 rounded-full border-2 border-panel ${
                  CORES_DA_SITUACAO[situacao.cor]
                }`}
              />
            )}
          </span>
          {!recolhido && (
            <span className="min-w-0 flex-1 truncate text-sm font-semibold tracking-[0.08em] text-texto">
              {nomeDoEspaco}
            </span>
          )}
          <button
            onClick={() => setGaveta(false)}
            aria-label="Fechar o menu"
            className="rounded-md p-1 text-muted hover:bg-surface hover:text-texto md:hidden"
          >
            <Icone nome="sys-close" tamanho={18} />
          </button>
        </div>

        <button
          onClick={() => setRecolhido((antes) => !antes)}
          aria-label={recolhido ? "Abrir o menu" : "Recolher o menu"}
          title={recolhido ? "Abrir o menu" : "Recolher o menu"}
          className="absolute -right-3 top-7 z-10 hidden h-6 w-6 items-center justify-center rounded-full border border-borda bg-panel text-dim transition-colors hover:border-dim hover:text-texto md:flex"
        >
          <Icone
            nome="sys-chevron"
            tamanho={14}
            className={`transition-transform ${recolhido ? "" : "rotate-180"}`}
          />
        </button>

        <nav className="min-h-0 flex-1 overflow-y-auto px-3 pb-3">
          {GRUPOS.map((grupo, i) => (
            <div
              key={grupo.titulo}
              className={
                recolhido
                  ? `${i > 0 ? "mt-2 border-t border-borda pt-2" : ""}`
                  : "mb-5 last:mb-0"
              }
            >
              {!recolhido && <p className="rotulo mb-1.5 px-3">{grupo.titulo}</p>}
              <ul className="flex flex-col gap-0.5">
                {grupo.itens.map((item) => (
                  <li key={item.para}>
                    {item.embreve ? (
                      <span
                        aria-disabled="true"
                        title={item.texto + " (em breve)"}
                        className={`flex cursor-not-allowed items-center gap-3 rounded-md px-3 py-2 text-sm text-dim ${
                          recolhido ? "justify-center" : ""
                        }`}
                      >
                        <Icone nome={item.icone} tamanho={18} />
                        {!recolhido && (
                          <>
                            <span className="flex-1 truncate">{item.texto}</span>
                            <span className="rounded-full border border-borda px-1.5 py-px text-[0.5625rem] uppercase tracking-[0.06em]">
                              em breve
                            </span>
                          </>
                        )}
                      </span>
                    ) : (
                      <NavLink
                        to={item.para}
                        end={item.fim}
                        title={recolhido ? item.texto : undefined}
                        aria-label={recolhido ? item.texto : undefined}
                        className={({ isActive }) =>
                          `flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors ${
                            recolhido ? "justify-center" : ""
                          } ${
                            isActive
                              ? "bg-ciano/10 font-medium text-ciano"
                              : "text-muted hover:bg-surface hover:text-texto"
                          }`
                        }
                      >
                        <Icone nome={item.icone} tamanho={18} />
                        {!recolhido && <span className="truncate">{item.texto}</span>}
                      </NavLink>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </nav>

        {/* A área da conta: quem está dentro e para onde ir mexer na instalação. A situação subiu
            para a marca, no topo. O copiloto entra logo acima dela: ele era um botão flutuante no
            canto, que tapava conteúdo em toda tela para uma coisa que se usa de vez em quando. */}
        <div className="border-t border-borda p-3">
          {aoAbrirCopiloto && !copilotoAberto && (
            <button
              onClick={aoAbrirCopiloto}
              title={recolhido ? "Copiloto" : undefined}
              aria-label={recolhido ? "Copiloto" : undefined}
              className={`mb-3 flex w-full items-center gap-3 rounded-md border border-ciano/40 px-3 py-2 text-sm text-ciano transition-colors hover:bg-ciano/10 ${
                recolhido ? "justify-center px-0" : ""
              }`}
            >
              <Icone nome="comm-chat" tamanho={18} />
              {!recolhido && <span className="truncate">Copiloto</span>}
            </button>
          )}
          <NavLink
            to="/configuracoes"
            title={recolhido ? "Perfil e configurações" : undefined}
            aria-label={recolhido ? "Perfil e configurações" : undefined}
            className={({ isActive }) =>
              recolhido
                ? `mx-auto flex h-9 w-9 items-center justify-center rounded-full border transition-colors ${
                    isActive
                      ? "border-ciano/40 bg-ciano/10 text-ciano"
                      : "border-borda text-muted hover:text-texto"
                  }`
                : `flex items-center gap-3 rounded-md px-2 py-2 transition-colors ${
                    isActive ? "bg-ciano/10 text-ciano" : "text-muted hover:bg-surface hover:text-texto"
                  }`
            }
          >
            {recolhido ? (
              <Icone nome="nav-user" tamanho={16} />
            ) : (
              <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-borda">
                <Icone nome="nav-user" tamanho={16} />
              </span>
            )}
            {!recolhido && (
              <span className="min-w-0 flex-1">
                <span className="block truncate text-sm">{quemOpera}</span>
                <span className="block truncate text-xs text-dim">{endereco}</span>
              </span>
            )}
            {!recolhido && <Icone nome="sys-chevron" tamanho={14} className="text-dim" />}
          </NavLink>
        </div>
      </aside>

      {/* Sem barra do topo: ela ocupava uma faixa inteira para uma busca desligada e um ponto de
          situação. No celular sobra o abridor da gaveta, solto sobre o conteúdo. */}
      {!gaveta && (
        <button
          onClick={() => setGaveta(true)}
          aria-label="Abrir o menu"
          className="fixed left-4 top-4 z-30 flex items-center gap-2 rounded-md border border-borda bg-panel px-3 py-2 text-sm text-texto shadow-alto transition-colors hover:border-dim md:hidden"
        >
          <Icone nome="sys-menu" tamanho={16} />
          Menu
        </button>
      )}

      <main className="min-w-0 flex-1 overflow-y-auto p-4 pt-16 md:p-10">
        <div className="mx-auto w-full max-w-6xl">{children}</div>
      </main>

      {copiloto}
    </div>
  );
}
