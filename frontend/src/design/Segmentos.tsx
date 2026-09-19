/** As opções lado a lado do cabeçalho: período, situação do agente, situação da conversa.
 *
 *  Cada tela desenhava o próprio grupo, com altura, arredondamento e peso de fonte diferentes, ao
 *  lado de uma lupa de 44px: três controles para a mesma coisa. Aqui é um só, na altura de todos os
 *  outros do cabeçalho.
 *
 *  Uma escolha por vez, e sempre há uma escolhida: `aria-pressed` diz qual, como num grupo de
 *  botões de alternância.
 */
export function Segmentos<T>({
  rotulo,
  opcoes,
  valor,
  aoMudar,
}: {
  /** O que se escolhe, para o leitor de tela: "Período". */
  rotulo: string;
  opcoes: { rotulo: string; valor: T }[];
  valor: T;
  aoMudar: (valor: T) => void;
}) {
  return (
    <div
      role="group"
      aria-label={rotulo}
      className="flex h-11 items-center gap-0.5 rounded-md border border-borda p-1"
    >
      {opcoes.map((o) => (
        <button
          key={o.rotulo}
          onClick={() => aoMudar(o.valor)}
          aria-pressed={o.valor === valor}
          className={`h-full whitespace-nowrap rounded px-3.5 text-sm transition-colors ${
            o.valor === valor
              ? "bg-texto font-medium text-void"
              : "text-muted hover:text-texto"
          }`}
        >
          {o.rotulo}
        </button>
      ))}
    </div>
  );
}
