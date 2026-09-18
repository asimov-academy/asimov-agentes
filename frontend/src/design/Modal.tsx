import { useEffect, useRef, type ReactNode } from "react";
import { Icone } from "./Icone";

/** O popup grande do painel. Regra do operador: **toda configuração de agente acontece aqui**, com
 *  o que está atrás embaçado e escurecido, para o foco ficar no agente.
 *
 *  O design system não traz um modal pronto, então ele é montado com as primitivas dele: fundo
 *  `surface`, borda de 1px, cantos retos, os dois cantos marcados em SVG do botão fantasma, e o
 *  rótulo em mono no topo. O embaçado é do navegador (`backdrop-blur`), não uma cor nova.
 *
 *  Comportamento: Esc fecha, clicar no fundo fecha, o corpo da página para de rolar enquanto ele
 *  está aberto, e o foco vai para o popup ao abrir e volta para quem o abriu ao fechar.
 */
export function Modal({
  titulo,
  subtitulo,
  aoFechar,
  children,
  rodape,
  largura = "max-w-5xl",
}: {
  titulo: string;
  subtitulo?: string;
  aoFechar: () => void;
  children: ReactNode;
  rodape?: ReactNode;
  largura?: string;
}) {
  const caixa = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const antes = document.activeElement as HTMLElement | null;
    const rolagem = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    caixa.current?.focus();

    const tecla = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.stopPropagation();
        aoFechar();
      }
      // O Tab não escapa do popup: sem isso o foco desce para a lista embaçada atrás.
      if (e.key === "Tab" && caixa.current) {
        const focaveis = caixa.current.querySelectorAll<HTMLElement>(
          'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
        );
        if (focaveis.length === 0) return;
        const primeiro = focaveis[0];
        const ultimo = focaveis[focaveis.length - 1];
        if (!e.shiftKey && document.activeElement === ultimo) {
          e.preventDefault();
          primeiro.focus();
        } else if (e.shiftKey && document.activeElement === primeiro) {
          e.preventDefault();
          ultimo.focus();
        }
      }
    };
    document.addEventListener("keydown", tecla, true);
    return () => {
      document.removeEventListener("keydown", tecla, true);
      document.body.style.overflow = rolagem;
      antes?.focus?.();
    };
  }, [aoFechar]);

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto p-4 md:items-center md:p-8">
      {/* O que está atrás: escurecido e embaçado. */}
      <div
        className="fixed inset-0 bg-void/80 backdrop-blur-md"
        onClick={aoFechar}
        aria-hidden="true"
      />

      <div
        ref={caixa}
        role="dialog"
        aria-modal="true"
        aria-label={titulo}
        tabIndex={-1}
        className={`relative my-auto w-full ${largura} border border-borda bg-surface shadow-ativo focus:outline-none`}
      >
        {/* Os dois cantos marcados, a assinatura do design system. */}
        <svg viewBox="0 0 12 12" className="pointer-events-none absolute -left-px -top-px h-3 w-3 text-ciano">
          <path d="M0 12V0H12" stroke="currentColor" fill="none" strokeWidth={2} />
        </svg>
        <svg viewBox="0 0 12 12" className="pointer-events-none absolute -bottom-px -right-px h-3 w-3 text-ciano">
          <path d="M12 0V12H0" stroke="currentColor" fill="none" strokeWidth={2} />
        </svg>

        <header className="flex items-start justify-between gap-6 border-b border-borda p-6 md:p-8">
          <div className="min-w-0">
            <h2 className="text-2xl font-semibold tracking-tight text-texto">{titulo}</h2>
            {subtitulo && <p className="mt-1 text-sm text-muted">{subtitulo}</p>}
          </div>
          <button
            onClick={aoFechar}
            aria-label="Fechar"
            className="shrink-0 border border-borda p-2 text-muted transition-colors hover:border-texto/40 hover:text-texto"
          >
            <Icone nome="sys-close" tamanho={16} />
          </button>
        </header>

        <div className="p-6 md:p-8">{children}</div>

        {rodape && (
          <footer className="flex flex-wrap items-center justify-end gap-3 border-t border-borda p-6 md:px-8">
            {rodape}
          </footer>
        )}
      </div>
    </div>
  );
}
