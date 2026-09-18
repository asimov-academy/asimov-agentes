import { useId } from "react";

/** Faixa de escolha: opções em ordem, arrastadas como o volume, em vez de um botão por opção.
 *
 *  Botão por opção obriga a ler quatro rótulos para descobrir que existe uma ordem entre eles.
 *  A faixa mostra a ordem no próprio desenho: o operador arrasta para mais ou para menos e lê o
 *  rótulo escolhido em cima. Serve para toda escolha de grau (emoji hoje, ritmo depois).
 */
export function Faixa<V extends string>({
  rotulo,
  opcoes,
  valor,
  aoMudar,
  ajuda,
}: {
  rotulo: string;
  opcoes: { valor: V; rotulo: string }[];
  valor: V;
  aoMudar: (novo: V) => void;
  ajuda?: string;
}) {
  const id = useId();
  const posicao = Math.max(
    0,
    opcoes.findIndex((o) => o.valor === valor),
  );
  const escolhida = opcoes[posicao];

  return (
    <div>
      <div className="flex items-baseline justify-between gap-4">
        <label htmlFor={id} className="rotulo cursor-pointer">
          {rotulo}
        </label>
        <span className="text-sm text-texto">{escolhida?.rotulo}</span>
      </div>

      <input
        id={id}
        type="range"
        min={0}
        max={opcoes.length - 1}
        step={1}
        value={posicao}
        aria-label={rotulo}
        aria-valuetext={escolhida?.rotulo}
        onChange={(e) => aoMudar(opcoes[Number(e.target.value)].valor)}
        className="mt-3 w-full cursor-pointer accent-ciano"
      />

      {/* Os extremos, que é o que diz para que lado arrastar. O do meio o operador descobre
          arrastando, e escrever os quatro embaixo de uma faixa estreita vira sopa de letra. */}
      <div className="mt-1 flex justify-between text-xs text-muted">
        <span>{opcoes[0]?.rotulo}</span>
        <span>{opcoes[opcoes.length - 1]?.rotulo}</span>
      </div>

      {ajuda && <p className="mt-2 text-sm text-dim">{ajuda}</p>}
    </div>
  );
}
