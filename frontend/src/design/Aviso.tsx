import type { ReactNode } from "react";
import { Icone } from "./Icone";
import type { ICONES } from "./icones";

/** O alerta do design system (seção 5, "05 // SYSTEM STATUS"): borda de 4px à esquerda na cor do
 *  tom, ícone do sprite, título curto em maiúsculo e o texto em mono. */
type Tom = "erro" | "atencao" | "informacao" | "ok";

const TONS: Record<Tom, { borda: string; cor: string; icone: keyof typeof ICONES }> = {
  erro: { borda: "border-l-perigo", cor: "text-perigo", icone: "stat-error" },
  atencao: { borda: "border-l-atencao", cor: "text-atencao", icone: "stat-warning" },
  informacao: { borda: "border-l-lime", cor: "text-lime", icone: "stat-info" },
  ok: { borda: "border-l-ok", cor: "text-ok", icone: "stat-success" },
};

export function Aviso({
  tom = "informacao",
  titulo,
  children,
}: {
  tom?: Tom;
  titulo: string;
  children?: ReactNode;
}) {
  const t = TONS[tom];
  return (
    <div
      role={tom === "erro" ? "alert" : "status"}
      className={`flex items-start gap-4 border border-l-4 border-borda bg-surface p-4 ${t.borda}`}
    >
      <Icone nome={t.icone} tamanho={20} className={`mt-0.5 ${t.cor}`} />
      <div>
        <h4 className={`text-xs font-bold uppercase tracking-wide ${t.cor}`}>{titulo}</h4>
        {children && <p className="mt-1 font-mono text-xs text-dim">{children}</p>}
      </div>
    </div>
  );
}
