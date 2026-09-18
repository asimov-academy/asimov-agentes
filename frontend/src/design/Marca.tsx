import { MARCAS, type NomeDeMarca } from "./marcas";

/** O logo de uma integração, na cor do texto em volta.
 *
 *  Diferente do `Icone` só no preenchimento: marca é `fill`, ícone é `stroke`. A cor vem da paleta
 *  do painel, nunca da marca: verde do WhatsApp e azul do Chatwoot ao lado do ciano brigam com a
 *  interface e cada linha da lista puxa para um lado.
 */
export function Marca({
  nome,
  tamanho = 20,
  className = "",
}: {
  nome: NomeDeMarca;
  tamanho?: number;
  className?: string;
}) {
  return (
    <svg
      viewBox="0 0 24 24"
      width={tamanho}
      height={tamanho}
      fill="currentColor"
      aria-hidden="true"
      focusable="false"
      className={`shrink-0 ${className}`}
      dangerouslySetInnerHTML={{ __html: `<path d="${MARCAS[nome]}" />` }}
    />
  );
}
