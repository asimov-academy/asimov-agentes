import type { ReactNode } from "react";
import { Icone } from "./Icone";
import type { ICONES } from "./icones";

/** O alerta do design system (seção 5, "05 // SYSTEM STATUS"): barra fina à esquerda na cor do
 *  tom, ícone do sprite, título curto em maiúsculo e o texto em mono. */
type Tom = "erro" | "atencao" | "informacao" | "ok";

const TONS: Record<Tom, { barra: string; cor: string; icone: keyof typeof ICONES }> = {
  erro: { barra: "bg-perigo", cor: "text-perigo", icone: "stat-error" },
  atencao: { barra: "bg-atencao", cor: "text-atencao", icone: "stat-warning" },
  informacao: { barra: "bg-ciano", cor: "text-ciano", icone: "stat-info" },
  ok: { barra: "bg-ok", cor: "text-ok", icone: "stat-success" },
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
      className="relative flex items-start gap-3 rounded-lg border border-borda bg-surface p-4 pl-5"
    >
      <span aria-hidden="true" className={`absolute inset-y-3 left-2 w-0.5 rounded-full ${t.barra}`} />
      <Icone nome={t.icone} tamanho={20} className={`mt-0.5 ${t.cor}`} />
      <div>
        <h4 className={`text-sm font-semibold ${t.cor}`}>{titulo}</h4>
        {children && <p className="mt-1 text-sm leading-snug text-muted">{children}</p>}
      </div>
    </div>
  );
}
