/** O "SVG GAUGE" do design system: anel de 2px com o arco em lime e brilho, e o número em mono
 *  no centro. É o que a Visão geral usa para proporção (saúde, uso, corte). */
const ARCO = "M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831";

export function Medidor({ parte, de = 100, rotulo }: { parte: number; de?: number; rotulo?: string }) {
  const porcento = de > 0 ? Math.max(0, Math.min(100, Math.round((parte / de) * 100))) : 0;
  return (
    <div className="flex items-center gap-4">
      <div className="relative h-16 w-16">
        <svg viewBox="0 0 36 36" className="h-full w-full -rotate-90">
          <path className="text-dim" d={ARCO} fill="none" stroke="currentColor" strokeWidth={2} />
          <path
            className="text-lime drop-shadow-lime"
            strokeDasharray={`${porcento}, 100`}
            d={ARCO}
            fill="none"
            stroke="currentColor"
            strokeWidth={2}
            strokeLinecap="round"
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center font-mono text-xs font-bold">
          {porcento}%
        </div>
      </div>
      {rotulo && <span className="rotulo">{rotulo}</span>}
    </div>
  );
}
