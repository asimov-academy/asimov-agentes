import type { Situacao } from "../../api/cliente";

/** As três situações do agente, com o que cada uma quer dizer na prática.
 *
 *  O agente sem canal externo está sempre em treinamento: ele fala só com quem o está ajustando, e
 *  é o backend que recusa marcá-lo como ativo. Conectar um canal o tira do treinamento sozinho.
 */
export const SITUACOES: {
  valor: Situacao;
  rotulo: string;
  tom: "ok" | "atencao" | "perigo";
  cor: string;
  explica: string;
}[] = [
  {
    valor: "ativo",
    rotulo: "Ativo",
    tom: "ok",
    cor: "bg-ok",
    explica: "Atende no canal dele e aqui no painel.",
  },
  {
    valor: "treinamento",
    rotulo: "Em treinamento",
    tom: "atencao",
    cor: "bg-atencao",
    explica: "Responde só aqui no painel. Quem chega pelo canal não fala com ele.",
  },
  {
    valor: "inativo",
    rotulo: "Desativado",
    tom: "perigo",
    cor: "bg-perigo",
    explica: "Calado em todo lugar. A mensagem chega e ninguém responde.",
  },
];

export const SITUACAO = (qual: Situacao) => SITUACOES.find((s) => s.valor === qual) ?? SITUACOES[0];
