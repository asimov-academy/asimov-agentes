import { Icone } from "./Icone";

/** O stepper do design system (seção 5, "04 // WAYFINDING"), na vertical.
 *
 *  O original é horizontal, com o círculo de 32px, o traço entre eles, o certo no passo pronto, o
 *  ponto pulsando no passo atual e o número no que falta. Aqui ele fica em coluna, porque o popup
 *  do agente tem sete passos e nome de passo não cabe lado a lado. As três formas são as mesmas.
 */
export function Passos({
  passos,
  atual,
  aoIr,
}: {
  passos: string[];
  atual: number;
  /** Voltar a um passo já respondido. O que ainda não foi respondido não é clicável. */
  aoIr?: (indice: number) => void;
}) {
  return (
    <ol className="flex gap-2 overflow-x-auto md:flex-col md:gap-0 md:overflow-visible">
      {passos.map((passo, i) => {
        const pronto = i < atual;
        const agora = i === atual;
        const podeIr = pronto && aoIr;
        return (
          <li key={passo} className="flex shrink-0 items-center gap-3 md:items-stretch">
            <div className="flex flex-col items-center">
              <span
                className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full border ${
                  pronto
                    ? "border-ciano bg-ciano/10 text-ciano"
                    : agora
                      ? "border-texto bg-void text-texto shadow-ativo"
                      : "border-dim bg-void text-dim"
                }`}
              >
                {pronto ? (
                  <Icone nome="act-check" tamanho={14} />
                ) : agora ? (
                  <span className="h-2 w-2 animate-pulse rounded-full bg-texto" />
                ) : (
                  <span className="font-mono text-xs">{i + 1}</span>
                )}
              </span>
              {i < passos.length - 1 && (
                <span className={`hidden w-px flex-1 md:block ${pronto ? "bg-ciano" : "bg-dim"}`} />
              )}
            </div>

            <div className="md:pb-8 md:pt-1.5">
              {podeIr ? (
                <button
                  onClick={() => aoIr(i)}
                  className="whitespace-nowrap text-left text-sm text-muted transition-colors hover:text-texto"
                >
                  {passo}
                </button>
              ) : (
                <span
                  aria-current={agora ? "step" : undefined}
                  className={`block whitespace-nowrap text-sm ${agora ? "text-texto" : "text-dim"}`}
                >
                  {passo}
                </span>
              )}
            </div>
          </li>
        );
      })}
    </ol>
  );
}
