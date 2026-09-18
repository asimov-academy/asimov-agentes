import type { NomeDeMarca } from "../../design/marcas";

/** O texto de cada canal: o que ele serve, o que ele exige antes de começar e o que custa.
 *
 *  Mora no front porque é copy de tela. A verdade de quais canais existem vem do
 *  `GET /painel/api/canais`, e canal que aparecer ali sem texto aqui ainda funciona, só sem a
 *  explicação. Um teste confere que os quatro de hoje têm texto.
 *
 *  O "custo de entrada" é a informação que falta em todo onboarding: dizer antes o que a pessoa vai
 *  precisar ter na mão, para ela não descobrir no meio do caminho que precisa do celular.
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
    rotulo: "Só conversa de teste",
    serve: "O agente responde no painel e no terminal, sem falar com ninguém de fora.",
    exige: "nada. Dá para conectar a um canal depois",
    marca: "terminal",
  },
  chatwoot: {
    rotulo: "Chatwoot",
    serve: "O agente atende nas caixas do seu Chatwoot e passa para a equipe quando precisa.",
    exige: "o endereço do Chatwoot e um token de administrador",
    marca: "chatwoot",
  },
  waha: {
    rotulo: "WhatsApp pelo aparelho",
    serve: "Um número comum de WhatsApp, conectado por QR code, como um aparelho a mais.",
    exige: "o celular com o número na mão, para ler o QR code agora",
    atencao: "Não é a API oficial: a Meta pode bloquear o número sem aviso. Use um chip só do agente.",
    marca: "whatsapp",
  },
  whatsapp: {
    rotulo: "WhatsApp oficial",
    serve: "Número da Cloud API da Meta, homologado, que não roda no celular de ninguém.",
    exige: "app na Meta, token permanente e a chave secreta do app",
    atencao: "A Meta cobra por mensagem, com 1.000 grátis por número por mês.",
    marca: "meta",
  },
};

export const ROTULO_DO_CANAL = (nome: string) => CANAIS[nome]?.rotulo ?? nome;
