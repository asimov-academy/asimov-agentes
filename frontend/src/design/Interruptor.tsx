import { useId } from "react";

/** O interruptor: cápsula de 48x24 com o botão redondo de 16px, borda `borda` apagado e `ciano`
 *  ligado, com o fundo em `ciano/10`. Era retângulo reto até a v0.21.0. */
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
        {descricao && <span className="mt-1 block text-sm leading-snug text-muted">{descricao}</span>}
      </label>

      <button
        id={id}
        type="button"
        role="switch"
        aria-checked={ligado}
        aria-label={rotulo}
        disabled={desligado}
        onClick={() => aoMudar(!ligado)}
        className={`relative h-6 w-12 shrink-0 rounded-full border transition-colors disabled:opacity-40 ${
          ligado ? "border-ciano bg-ciano/10" : "border-borda bg-surface"
        }`}
      >
        <span
          className={`absolute left-0.5 top-0.5 h-4 w-4 rounded-full transition-all duration-300 ${
            ligado ? "translate-x-6 bg-ciano" : "bg-dim"
          }`}
        />
      </button>
    </div>
  );
}
