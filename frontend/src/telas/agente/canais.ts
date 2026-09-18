import type { ICONES } from "../../design/icones";

/** O texto de cada canal: o que ele serve e o que ele exige antes de começar.
 *
 *  Mora no front porque é copy de tela. A verdade de quais canais existem vem do
 *  `GET /painel/api/canais`, e canal que aparecer ali sem texto aqui ainda funciona, só sem a
 *  explicação. Um teste confere que os quatro de hoje têm texto.
 *
 *  O "custo de entrada" é a informação que falta em todo onboarding: dizer antes o que a pessoa vai
 *  precisar ter na mão, para ela não descobrir no meio do caminho que precisa do celular.
 */
export type TextoDoCanal = {
  rotulo: string;
  serve: string;
  exige: string;
  icone: keyof typeof ICONES;
};

export const CANAIS: Record<string, TextoDoCanal> = {
  nativo: {
    rotulo: "Só conversa de teste",
    serve: "O agente responde no terminal e no painel, sem falar com ninguém de fora.",
    exige: "Nada. Dá para conectar a um canal depois.",
    icone: "comm-chat",
  },
  chatwoot: {
    rotulo: "Chatwoot",
    serve: "O agente atende nas caixas do seu Chatwoot e passa para a equipe quando precisa.",
    exige: "O endereço do Chatwoot e um token de administrador.",
    icone: "comm-comment",
  },
  waha: {
    rotulo: "WhatsApp pelo aparelho",
    serve: "Um número comum de WhatsApp, pareado por QR code. Não é a API oficial.",
    exige: "O celular com o número na mão para ler o QR code agora.",
    icone: "comm-phone",
  },
  whatsapp: {
    rotulo: "WhatsApp oficial",
    serve: "Número da Cloud API da Meta, com template aprovado para o aviso de handoff.",
    exige: "App na Meta, token permanente e a chave secreta do app.",
    icone: "comm-notify",
  },
};

export const ROTULO_DO_CANAL = (nome: string) => CANAIS[nome]?.rotulo ?? nome;
