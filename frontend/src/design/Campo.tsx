import { useId, type InputHTMLAttributes } from "react";
import { Icone } from "./Icone";
import type { ICONES } from "./icones";

/** O campo: moldura inteira arredondada, `borda` em repouso e `ciano` no foco, fundo `surface` e o
 *  ícone à esquerda. Era só borda de baixo até a v0.21.0, quando o painel deixou o canto reto. */
type Props = Omit<InputHTMLAttributes<HTMLInputElement>, "className"> & {
  rotulo?: string;
  icone?: keyof typeof ICONES;
  erro?: string;
};

export function Campo({ rotulo, icone, erro, ...resto }: Props) {
  const id = useId();
  return (
    <div className="w-full">
      {rotulo && (
        <label htmlFor={id} className="rotulo mb-2 block">
          {rotulo}
        </label>
      )}
      <div className="relative w-full">
        {icone && <Icone nome={icone} className="absolute left-3 top-2.5 text-dim" />}
        <input
          id={id}
          {...resto}
          aria-invalid={erro ? true : undefined}
          className={`w-full rounded-md border bg-surface px-3 py-2 text-sm text-texto transition-colors placeholder:text-dim focus:outline-none focus:ring-1 focus:ring-ciano ${
            icone ? "pl-9" : ""
          } ${erro ? "border-perigo" : "border-borda focus:border-ciano"}`}
        />
      </div>
      {erro && <p className="mt-2 text-xs text-perigo">{erro}</p>}
    </div>
  );
}
