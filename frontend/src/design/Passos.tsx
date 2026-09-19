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
  alcanca,
}: {
  passos: string[];
  atual: number;
  aoIr?: (indice: number) => void;
  /** Até que passo dá para ir, para frente e para trás. Sem isto, só para os já respondidos.
   *  Quem decide é a tela: passo com campo obrigatório vazio segura os seguintes. */
  alcanca?: number;
}) {
  return (
    <ol className="flex gap-2 overflow-x-auto md:flex-col md:gap-0 md:overflow-visible">
      {passos.map((passo, i) => {
        const pronto = i < atual;
        const agora = i === atual;
        const podeIr = aoIr && !agora && i <= (alcanca ?? atual - 1);
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
                  className="-my-2.5 min-h-11 whitespace-nowrap text-left text-sm text-muted transition-colors hover:text-texto"
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
