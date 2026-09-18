import { ICONES } from "./icones";

/** Ícone do sprite do design system. Traço de 2px na grade de 24px, sempre `currentColor`.
 *  Ícone que não existe no sprite não é desenhado à mão: entra no sprite primeiro. */
export function Icone({
  nome,
  tamanho = 16,
  className = "",
}: {
  nome: keyof typeof ICONES;
  tamanho?: number;
  className?: string;
}) {
  return (
    <svg
      viewBox="0 0 24 24"
      width={tamanho}
      height={tamanho}
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
      className={`shrink-0 ${className}`}
      dangerouslySetInnerHTML={{ __html: ICONES[nome] }}
    />
  );
}
