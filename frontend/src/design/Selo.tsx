/** Selo de situação: cápsula, Inter, 10px, maiúsculo. Era retângulo reto em mono até a v0.21.0. */
type Tom = "ok" | "atencao" | "perigo" | "neutro" | "acento";

const TONS: Record<Tom, string> = {
  ok: "border-ok/40 text-ok",
  atencao: "border-atencao/40 text-atencao",
  perigo: "border-perigo/40 text-perigo",
  neutro: "border-dim text-muted",
  acento: "border-ciano/40 text-ciano",
};

export function Selo({ tom = "neutro", children }: { tom?: Tom; children: string }) {
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-[0.625rem] font-semibold uppercase tracking-[0.08em] ${TONS[tom]}`}
    >
      {children}
    </span>
  );
}
