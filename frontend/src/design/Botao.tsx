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
 *
 *  Os cantos marcados do fantasma saíram junto com os cantos retos (v0.21.0): eles eram o desenho
 *  de um canto em ângulo, e não sobra canto em ângulo no painel.
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
  const tamanho = pequeno ? "rounded-md px-4 py-2 text-xs gap-2" : "rounded px-5 py-2.5 text-sm gap-2.5";
  return (
    <button
      {...resto}
      disabled={disabled || ocupado}
      aria-busy={ocupado || undefined}
      className={`group relative inline-flex items-center justify-center font-semibold tracking-[0.02em] transition-colors disabled:cursor-not-allowed disabled:opacity-40 ${tamanho} ${TONS[tom]} ${className}`}
    >
      {ocupado ? <Icone nome="sys-girando" className="animate-spin" /> : icone && <Icone nome={icone} />}
      <span>{children}</span>
    </button>
  );
}
