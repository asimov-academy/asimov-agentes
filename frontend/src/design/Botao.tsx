import type { ButtonHTMLAttributes } from "react";
import { Icone } from "./Icone";
import type { ICONES } from "./icones";

/** Os três botões do design system (seção 5, "01 // INTERACTIVE BUTTONS"), na hierarquia dele:
 *
 *  - `solido`: branco sobre preto. É o botão que conclui a ação, e é o mais forte da tela.
 *  - `acento`: contorno ciano que se preenche no hover. Ação afirmativa secundária.
 *  - `fantasma`: contorno branco fraco, com os cantos marcados. É o botão de andar pela tela.
 *
 *  O ciano cheio não é botão no original: ele é contorno. Trocar isso apaga a hierarquia inteira.
 */
type Tom = "solido" | "acento" | "fantasma" | "perigo";

const TONS: Record<Tom, string> = {
  solido: "bg-texto text-void border border-texto hover:bg-white",
  acento: "border border-ciano/50 text-ciano hover:bg-ciano hover:text-void",
  fantasma: "border border-texto/20 bg-transparent text-texto hover:bg-texto/5",
  perigo: "border border-perigo/50 text-perigo hover:bg-perigo hover:text-void",
};

type Props = ButtonHTMLAttributes<HTMLButtonElement> & {
  tom?: Tom;
  icone?: keyof typeof ICONES;
  pequeno?: boolean;
  ocupado?: boolean;
};

export function Botao({
  tom = "fantasma",
  icone,
  pequeno,
  ocupado,
  children,
  className = "",
  disabled,
  ...resto
}: Props) {
  const tamanho = pequeno ? "px-4 py-2 text-xs gap-2" : "px-6 py-3 text-sm gap-3";
  return (
    <button
      {...resto}
      disabled={disabled || ocupado}
      aria-busy={ocupado || undefined}
      className={`group relative inline-flex items-center justify-center overflow-hidden font-bold uppercase tracking-widest transition-colors disabled:cursor-not-allowed disabled:opacity-40 ${tamanho} ${TONS[tom]} ${className}`}
    >
      {ocupado ? (
        <svg viewBox="0 0 24 24" className="h-4 w-4 animate-spin" fill="none" stroke="currentColor" strokeWidth={3}>
          <circle cx="12" cy="12" r="10" strokeOpacity="0.25" />
          <path d="M12 2a10 10 0 0 1 10 10" strokeLinecap="round" />
        </svg>
      ) : (
        icone && <Icone nome={icone} />
      )}
      <span>{children}</span>

      {/* Cantos marcados: a assinatura do botão fantasma no design system. */}
      {tom === "fantasma" && (
        <>
          <svg viewBox="0 0 10 10" className="pointer-events-none absolute left-0 top-0 h-2 w-2 text-texto">
            <path d="M0 10V0H10" stroke="currentColor" fill="none" />
          </svg>
          <svg viewBox="0 0 10 10" className="pointer-events-none absolute bottom-0 right-0 h-2 w-2 text-texto">
            <path d="M10 0V10H0" stroke="currentColor" fill="none" />
          </svg>
        </>
      )}
    </button>
  );
}
