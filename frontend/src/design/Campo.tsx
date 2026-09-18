import { useId, type InputHTMLAttributes } from "react";
import { Icone } from "./Icone";
import type { ICONES } from "./icones";

/** O campo do design system: **só borda de baixo**, `dim` em repouso e `lime` no foco, fundo
 *  `surface` e o ícone à esquerda. Campo com moldura inteira é de outro sistema. */
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
        {icone && <Icone nome={icone} className="absolute left-0 top-2.5 text-dim" />}
        <input
          id={id}
          {...resto}
          aria-invalid={erro ? true : undefined}
          className={`w-full border-b bg-surface p-2 text-sm text-texto transition-colors placeholder:text-dim focus:outline-none ${
            icone ? "pl-8" : ""
          } ${erro ? "border-perigo" : "border-dim focus:border-lime"}`}
        />
      </div>
      {erro && <p className="mt-2 font-mono text-xs text-perigo">{erro}</p>}
    </div>
  );
}
