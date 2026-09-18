import type { ReactNode } from "react";

/** O cabeçalho de uma seção: título, uma linha de contexto e as ações, tudo na mesma faixa.
 *
 *  O título era `text-5xl` com o contexto embaixo e uma régua depois, e comia um terço da tela
 *  antes de qualquer conteúdo. Agora ele é `text-2xl`, o contexto vai ao lado quando cabe, e a
 *  régua encosta: quem abre a tela vê a lista, não o nome dela.
 */
export function Cabecalho({
  titulo,
  contexto,
  acoes,
}: {
  titulo: string;
  /** Uma linha curta: a contagem, o período, o que a tela mostra. */
  contexto?: ReactNode;
  acoes?: ReactNode;
}) {
  return (
    <header className="flex flex-wrap items-center justify-between gap-x-6 gap-y-3 border-b border-borda pb-4">
      <div className="flex min-w-0 flex-wrap items-baseline gap-x-3 gap-y-1">
        <h1 className="text-2xl font-semibold tracking-tight text-texto">
          {titulo}
          <span className="text-ciano">.</span>
        </h1>
        {contexto && <p className="text-sm text-muted">{contexto}</p>}
      </div>
      {acoes && <div className="flex flex-wrap items-center gap-2">{acoes}</div>}
    </header>
  );
}
