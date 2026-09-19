import type { ButtonHTMLAttributes } from "react";
import { Icone } from "./Icone";
import type { ICONES } from "./icones";

/** O botão que é só um ícone: 44px de alvo, nome acessível obrigatório e o texto abrindo no hover
 *  e no foco, como na `Dica`. Só CSS, sem biblioteca.
 *
 *  Serve para ação secundária que se repete na tela (anexar, gravar, melhorar com IA). Ação que
 *  conclui ou que apaga continua com palavra: ícone sozinho não carrega consequência.
 */
type Props = Omit<ButtonHTMLAttributes<HTMLButtonElement>, "children" | "aria-label"> & {
  icone: keyof typeof ICONES;
  /** O nome do botão, lido pelo leitor de tela e mostrado no hover. */
  rotulo: string;
  /** Uma frase a mais no hover, quando o nome sozinho não explica. */
  explica?: string;
  tom?: "neutro" | "acento" | "perigo";
  ocupado?: boolean;
  /** Para onde o texto abre. Embaixo da tela, abre para cima. */
  abre?: "cima" | "baixo";
  /** Por qual lado o texto se alinha. `fim` é o padrão, porque a maioria destes botões fica na
   *  direita; `inicio` é para os que ficam encostados na borda esquerda, onde o balão vazaria. */
  alinha?: "inicio" | "fim";
};

const TONS = {
  neutro: "text-muted hover:bg-texto/5 hover:text-texto",
  acento: "text-ciano hover:bg-ciano/10",
  perigo: "text-perigo hover:bg-perigo/10",
};

export function BotaoIcone({
  icone,
  rotulo,
  explica,
  tom = "neutro",
  ocupado,
  abre = "cima",
  alinha = "fim",
  disabled,
  className = "",
  ...resto
}: Props) {
  return (
    <span className="group/bi relative inline-flex shrink-0">
      <button
        type="button"
        {...resto}
        aria-label={rotulo}
        aria-busy={ocupado || undefined}
        disabled={disabled || ocupado}
        className={`flex h-11 w-11 items-center justify-center rounded-md transition-colors disabled:cursor-not-allowed disabled:opacity-40 ${TONS[tom]} ${className}`}
      >
        <Icone
          nome={ocupado ? "sys-girando" : icone}
          tamanho={20}
          className={ocupado ? "animate-spin" : ""}
        />
      </button>
      <span
        aria-hidden="true"
        className={`pointer-events-none absolute z-20 w-max max-w-[16rem] rounded-md border border-borda bg-panel px-2.5 py-1.5 text-xs leading-snug text-muted opacity-0 shadow-alto transition-opacity group-focus-within/bi:opacity-100 group-hover/bi:opacity-100 ${
          abre === "cima" ? "bottom-full mb-2" : "top-full mt-2"
        } ${alinha === "fim" ? "right-0" : "left-0"}`}
      >
        <span className="block font-semibold text-texto">{rotulo}</span>
        {explica}
      </span>
    </span>
  );
}
