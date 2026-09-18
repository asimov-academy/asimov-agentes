/** O "PROGRESS & METERS" da AXIS (design system, seção 2, cartão 6 "System Health").
 *
 *  Rótulo em mono à esquerda, valor à direita, trilho de 1px em `borda` e a barra por cima. É a
 *  forma do sistema para proporção em lista: uma linha por item, todas na mesma escala, o olho
 *  compara sozinho. Muito melhor que cinco números soltos um do lado do outro.
 */
type Tom = "texto" | "ciano" | "atencao" | "perigo";

const TONS: Record<Tom, string> = {
  texto: "bg-texto",
  ciano: "bg-ciano",
  atencao: "bg-atencao",
  perigo: "bg-perigo",
};

/** Como escrever o rótulo. O design system usa a barra para rótulo de dado ("CPU LOAD"), que é
 *  mono e maiúsculo. Nome de pessoa e identificador de modelo não são isso: pessoa se escreve como
 *  gente escreve, e `openai:gpt-4o-mini` em maiúscula deixa de ser o identificador que é. */
type Escrita = "dado" | "nome" | "token";

const ESCRITAS: Record<Escrita, string> = {
  dado: "font-mono text-xs uppercase tracking-[0.1em] text-muted",
  nome: "text-sm text-texto",
  token: "font-mono text-xs text-muted",
};

export function Progresso({
  rotulo,
  valor,
  de,
  escrito,
  tom = "texto",
  escrita = "dado",
}: {
  rotulo: string;
  valor: number;
  /** O teto da escala. Numa lista é o maior valor dela, para as linhas ficarem comparáveis. */
  de: number;
  /** O que aparece à direita. Sem isso, o próprio valor. */
  escrito?: string;
  tom?: Tom;
  escrita?: Escrita;
}) {
  const porcento = de > 0 ? Math.max(0, Math.min(100, (valor / de) * 100)) : 0;
  return (
    <div>
      <div className="mb-1 flex items-baseline justify-between gap-4">
        <span className={`truncate ${ESCRITAS[escrita]}`}>{rotulo}</span>
        <span className="shrink-0 font-mono text-xs text-texto">{escrito ?? valor}</span>
      </div>
      <div
        className="h-1 w-full overflow-hidden bg-borda"
        role="meter"
        aria-label={rotulo}
        aria-valuenow={valor}
        aria-valuemin={0}
        aria-valuemax={de}
      >
        <div
          className={`h-full transition-[width] duration-1000 ease-out ${TONS[tom]}`}
          style={{ width: `${porcento}%` }}
        />
      </div>
    </div>
  );
}
