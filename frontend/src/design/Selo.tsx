/** Selo de situação. Mesmo formato do design system: retângulo reto, mono, 10px, maiúsculo. */
type Tom = "ok" | "atencao" | "perigo" | "neutro" | "acento";

const TONS: Record<Tom, string> = {
  ok: "border-ok/40 text-ok",
  atencao: "border-atencao/40 text-atencao",
  perigo: "border-perigo/40 text-perigo",
  neutro: "border-dim text-muted",
  acento: "border-lime/40 text-lime",
};

export function Selo({ tom = "neutro", children }: { tom?: Tom; children: string }) {
  return (
    <span
      className={`inline-flex items-center border px-2 py-0.5 font-mono text-[0.625rem] font-bold uppercase tracking-[0.15em] ${TONS[tom]}`}
    >
      {children}
    </span>
  );
}
