import type { ReactNode } from "react";

/** O `.comp-card` do design system: borda de 1px, fundo `surface`, 2rem de respiro, 1.5rem de
 *  distância entre as partes e a borda clareando no hover. O rótulo é o `.comp-label`: mono,
 *  0.65rem, maiúsculo, espaçado. */
export function Cartao({
  titulo,
  acao,
  children,
  className = "",
}: {
  titulo?: string;
  acao?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section
      className={`relative flex flex-col gap-5 rounded-lg border border-borda bg-surface p-6 transition-colors hover:border-dim ${className}`}
    >
      {(titulo || acao) && (
        <header className="flex items-start justify-between gap-4">
          {titulo && <span className="rotulo">{titulo}</span>}
          {acao}
        </header>
      )}
      {children}
    </section>
  );
}
