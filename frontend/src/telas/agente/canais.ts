import type { NomeDeMarca } from "../../design/marcas";

/** O texto de cada canal: o que ele serve, o que ele exige antes de começar e o que custa.
 *
 *  Mora no front porque é copy de tela. A verdade de quais canais existem vem do
 *  `GET /painel/api/canais`, e canal que aparecer ali sem texto aqui ainda funciona, só sem a
 *  explicação. Um teste confere que os quatro de hoje têm texto.
 *
 *  O "custo de entrada" é a informação que falta em todo onboarding: dizer antes o que a pessoa vai
 *  precisar ter na mão, para ela não descobrir no meio do caminho que precisa do celular. Em frase
 *  curta: o cartão é para escolher de relance, não para ler.
 *
 *  `atencao` é a limitação que o terminal conta e o painel escondia (auditoria de copy de
 *  2026-09-18): o risco de bloqueio da API não oficial e a cobrança por mensagem da Meta. Quem
 *  escolhe o canal aqui precisa saber disso antes, não depois.
 */
export type TextoDoCanal = {
  rotulo: string;
  serve: string;
  exige: string;
  atencao?: string;
  marca: NomeDeMarca;
};

export const CANAIS: Record<string, TextoDoCanal> = {
  nativo: {
    rotulo: "Conversa de teste",
    serve: "Só no painel e no terminal.",
    exige: "nada",
    marca: "terminal",
  },
  chatwoot: {
    rotulo: "Chatwoot",
    serve: "Nas caixas do seu Chatwoot.",
    exige: "endereço e token de administrador",
    marca: "chatwoot",
  },
  waha: {
    rotulo: "WhatsApp WAHA",
    serve: "Um número comum, conectado por QR code.",
    exige: "o celular com o número na mão",
    atencao: "Não é a API oficial: a Meta pode bloquear o número sem aviso. Use um chip só do agente.",
    marca: "whatsapp",
  },
  whatsapp: {
    rotulo: "WhatsApp Cloud API",
    serve: "Número homologado na Meta, fora do celular.",
    exige: "app, token permanente e chave secreta",
    atencao: "A Meta cobra por mensagem, com 1.000 grátis por número por mês.",
    marca: "meta",
  },
};

export const ROTULO_DO_CANAL = (nome: string) => CANAIS[nome]?.rotulo ?? nome;
