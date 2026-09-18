import { useId } from "react";

/** O "MECHANICAL TOGGLE" do design system: retângulo de 48x24 com botão quadrado de 16px, borda
 *  `dim` apagado e `ciano` ligado, com o fundo em `ciano/10`. Nada de cápsula arredondada. */
export function Interruptor({
  ligado,
  aoMudar,
  rotulo,
  descricao,
  desligado,
}: {
  ligado: boolean;
  aoMudar: (novo: boolean) => void;
  rotulo: string;
  descricao?: string;
  desligado?: boolean;
}) {
  const id = useId();
  return (
    <div className="flex items-start justify-between gap-6 border-b border-borda py-4 last:border-b-0">
      <label htmlFor={id} className={`min-w-0 ${desligado ? "cursor-not-allowed" : "cursor-pointer"}`}>
        <span className={`block text-sm ${desligado ? "text-dim" : "text-texto"}`}>{rotulo}</span>
        {descricao && <span className="mt-1 block font-mono text-xs text-muted">{descricao}</span>}
      </label>

      <button
        id={id}
        type="button"
        role="switch"
        aria-checked={ligado}
        aria-label={rotulo}
        disabled={desligado}
        onClick={() => aoMudar(!ligado)}
        className={`relative h-6 w-12 shrink-0 border transition-colors disabled:opacity-40 ${
          ligado ? "border-ciano bg-ciano/10" : "border-dim bg-surface"
        }`}
      >
        <span
          className={`absolute left-0.5 top-0.5 h-4 w-4 transition-all duration-300 ${
            ligado ? "translate-x-6 bg-ciano" : "bg-dim"
          }`}
        />
      </button>
    </div>
  );
}
