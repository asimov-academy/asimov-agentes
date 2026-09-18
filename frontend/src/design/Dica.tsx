import type { ReactNode } from "react";
import { Icone } from "./Icone";
import type { ICONES } from "./icones";

/** Um aviso que só ocupa um ícone, e abre o texto ao passar o mouse ou ao receber o foco.
 *
 *  Serve para a ressalva que importa na hora de escolher, mas que não pode roubar o cartão inteiro:
 *  o risco de bloqueio da API não oficial, a cobrança por mensagem da Meta. Com o texto aberto, o
 *  cartão tinha mais aviso do que descrição.
 *
 *  Só CSS, sem biblioteca. Abre no `hover` e no `focus-within`, para chegar pelo teclado; o texto
 *  fica no DOM o tempo todo, então leitor de tela o lê junto com o gatilho.
 */
export function Dica({
  texto,
  icone = "stat-warning",
  tom = "atencao",
  children,
}: {
  texto: string;
  icone?: keyof typeof ICONES;
  tom?: "atencao" | "muted";
  /** O gatilho. Sem nada, o gatilho é o próprio ícone. */
  children?: ReactNode;
}) {
  return (
    <span className="group/dica relative inline-flex">
      <span
        tabIndex={0}
        role="note"
        aria-label={texto}
        className={`inline-flex cursor-help items-center rounded-full outline-none ${
          tom === "atencao" ? "text-atencao" : "text-dim"
        }`}
      >
        {children ?? <Icone nome={icone} tamanho={16} />}
      </span>

      <span
        aria-hidden="true"
        className="pointer-events-none absolute bottom-full left-1/2 z-20 mb-2 w-56 -translate-x-1/2 rounded-md border border-borda bg-panel p-2.5 text-xs leading-snug text-muted opacity-0 shadow-alto transition-opacity group-hover/dica:opacity-100 group-focus-within/dica:opacity-100"
      >
        {texto}
      </span>
    </span>
  );
}
