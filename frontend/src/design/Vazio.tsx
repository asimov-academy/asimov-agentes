import type { ReactNode } from "react";
import { Icone } from "./Icone";
import type { ICONES } from "./icones";

/** Estado vazio no formato da zona de arraste do design system: tracejado `dim` que vira `lime`
 *  no hover, ícone do sprite num círculo apagado e o texto embaixo. */
export function Vazio({
  titulo,
  icone = "stat-info",
  children,
}: {
  titulo: string;
  icone?: keyof typeof ICONES;
  children?: ReactNode;
}) {
  return (
    <div className="group flex w-full flex-col items-center justify-center gap-3 border border-dashed border-dim p-8 text-center transition-colors hover:border-lime">
      <div className="flex h-10 w-10 items-center justify-center rounded-full bg-dim/20">
        <Icone nome={icone} tamanho={20} className="text-dim transition-colors group-hover:text-lime" />
      </div>
      <p className="rotulo">{titulo}</p>
      {children && <div className="font-mono text-xs text-dim">{children}</div>}
    </div>
  );
}
