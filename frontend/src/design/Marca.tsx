import { COR_DA_MARCA, MARCAS, type NomeDeMarca } from "./marcas";

/** O logo de uma integração, na cor da marca.
 *
 *  Diferente do `Icone`: marca é preenchida, não traçada, e não muda de cor com o texto em volta,
 *  porque é o logo de outra empresa. Com `apagada`, ela herda a cor do texto, para quando o canal
 *  está desligado ou o contraste com o fundo não ajuda.
 */
export function Marca({
  nome,
  tamanho = 20,
  apagada = false,
  className = "",
}: {
  nome: NomeDeMarca;
  tamanho?: number;
  apagada?: boolean;
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
      className={`shrink-0 ${apagada ? "text-dim" : COR_DA_MARCA[nome]} ${className}`}
      dangerouslySetInnerHTML={{ __html: `<path d="${MARCAS[nome]}" />` }}
    />
  );
}
