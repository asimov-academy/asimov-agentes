import { useEffect, useState } from "react";
import { api, type EspacoDeTrabalho, type Eu, type VinculoDeIa } from "../api/cliente";
import { Aviso } from "../design/Aviso";
import { Botao } from "../design/Botao";
import { Cabecalho } from "../design/Cabecalho";
import { Campo } from "../design/Campo";
import { Cartao } from "../design/Cartao";
import { Carregando } from "../design/Carregando";
import { Selo } from "../design/Selo";

/** A conta do operador, o espaço de trabalho e o assistente de código que move o copiloto.
 *
 *  **Não é o painel de controle da instalação.** Duas coisas saíram daqui em 2026-09-18:
 *
 *  - **Chaves de IA.** A IA é escolha de cada agente, e a chave passou a ser pedida onde o modelo é
 *    escolhido, na aba Configurações da ficha. Uma lista de provedores numa tela geral fazia
 *    parecer que a instalação tem uma IA, quando cada agente tem a sua.
 *  - **Os endereços e as contagens da instalação.** Subdomínio do painel, subdomínio dos agentes,
 *    quantas empresas e quantos agentes não se configuram: são fato, e fato de plantão é a Visão
 *    geral. O que restou aqui é o que o operador edita ou precisa saber para editar.
 *
 *  O que ficou de IA é o **assistente de código**, que é escolha da instalação mesmo: Claude Code
 *  ou Codex, pela assinatura do operador, e é ele que move o copiloto do painel.
 */
function Secao({
  titulo,
  ajuda,
  campos,
  valores,
  aoMudar,
  aoSalvar,
  rotuloDoBotao,
  rodape,
}: {
  titulo: string;
  ajuda?: string;
  campos: { campo: string; rotulo: string; placeholder?: string; tipo?: string }[];
  valores: Record<string, string>;
  aoMudar: (campo: string, valor: string) => void;
  aoSalvar: () => Promise<void>;
  rotuloDoBotao: string;
  rodape?: React.ReactNode;
}) {
  const [salvando, setSalvando] = useState(false);
  const [feito, setFeito] = useState(false);
  const [erro, setErro] = useState("");

  async function salva() {
    setSalvando(true);
    setErro("");
    setFeito(false);
    try {
      await aoSalvar();
      setFeito(true);
    } catch (problema) {
      setErro((problema as Error).message);
    } finally {
      setSalvando(false);
    }
  }

  return (
    <Cartao titulo={titulo}>
      {ajuda && <p className="max-w-[70ch] text-sm text-muted">{ajuda}</p>}

      <div className="grid gap-4 sm:grid-cols-2">
        {campos.map((c) => (
          <Campo
            key={c.campo}
            rotulo={c.rotulo}
            type={c.tipo ?? "text"}
            placeholder={c.placeholder}
            value={valores[c.campo] ?? ""}
            onChange={(e) => aoMudar(c.campo, e.target.value)}
          />
        ))}
      </div>

      {erro && (
        <Aviso tom="erro" titulo="não deu para salvar">
          {erro}
        </Aviso>
      )}

      <div className="flex flex-wrap items-center justify-between gap-4">
        <Botao icone="act-save" pequeno ocupado={salvando} onClick={salva}>
          {feito ? "Salvo" : rotuloDoBotao}
        </Botao>
        {rodape}
      </div>
    </Cartao>
  );
}

/** Quem move o copiloto: o CLI em que o operador entrou na instalação. Só de leitura. */
function AssistenteDeCodigo() {
  const [vinculo, setVinculo] = useState<VinculoDeIa | null>(null);
  const [erro, setErro] = useState("");

  useEffect(() => {
    api
      .copiloto()
      .then((estado) => setVinculo(estado.vinculo))
      .catch((problema) => setErro((problema as Error).message));
  }, []);

  return (
    <Cartao titulo="Assistente de código">
      <p className="max-w-[70ch] text-sm text-muted">
        É ele que move o copiloto do painel, rodando pela sua assinatura, sem chave de API e sem
        custo por mensagem. A IA que responde aos contatos é outra coisa: essa é de cada agente, na
        ficha dele.
      </p>

      {erro ? (
        <Aviso tom="erro" titulo="não deu para ver o vínculo">
          {erro}
        </Aviso>
      ) : !vinculo ? (
        <Carregando tipo="pontos" o_que="vendo o vínculo" />
      ) : (
        <div className="flex flex-wrap items-center gap-3">
          <span className="text-sm text-texto">{vinculo.nome}</span>
          {vinculo.vinculada ? <Selo tom="ok">conta vinculada</Selo> : <Selo>sem conta</Selo>}
          {vinculo.vinculada && vinculo.conta && (
            <span className="tecnico text-sm text-muted">{vinculo.conta}</span>
          )}
        </div>
      )}

      <p className="text-sm text-dim">
        {vinculo?.vinculada
          ? "Para trocar de assistente ou sair da conta, rode "
          : "Para ligar o copiloto, rode "}
        <span className="tecnico text-muted">{vinculo?.comando || "asimov ia"}</span> na VPS. A
        credencial fica onde o CLI oficial guarda, nunca no banco nem no painel.
      </p>
    </Cartao>
  );
}

export function Configuracoes({ eu, aoMudarConta }: { eu: Eu | null; aoMudarConta: () => void }) {
  const [espaco, setEspaco] = useState<EspacoDeTrabalho | null>(null);
  const [perfil, setPerfil] = useState<{ nome: string; email: string } | null>(null);

  // O formulário só nasce quando o `eu` chega: antes disso não há o que editar.
  useEffect(() => {
    if (!eu?.espaco) return;
    setEspaco(eu.espaco);
    setPerfil({ nome: eu.operador?.nome ?? "", email: eu.operador?.email ?? "" });
  }, [eu]);

  const mudaEspaco = (campo: string, valor: string) =>
    setEspaco((antes) => (antes ? { ...antes, [campo]: valor } : antes));

  return (
    <>
      <Cabecalho
        titulo="Configurações"
        contexto="Sua conta e o assistente que opera a plataforma. A IA de cada agente fica na ficha dele."
      />

      {espaco && perfil ? (
        <div className="mt-6 grid gap-4">
          <Secao
            titulo="Sua conta"
            ajuda="Quem administra esta instalação. Não serve para entrar: a senha continua a única credencial, e ela se troca com asimov painel na VPS."
            campos={[
              { campo: "nome", rotulo: "Seu nome", placeholder: "como você quer ser chamado" },
              { campo: "email", rotulo: "Seu e-mail", tipo: "email", placeholder: "para contato, não para entrar" },
            ]}
            valores={perfil}
            aoMudar={(campo, valor) => setPerfil((antes) => (antes ? { ...antes, [campo]: valor } : antes))}
            rotuloDoBotao="Salvar a conta"
            aoSalvar={async () => {
              await api.gravaPerfilDoOperador(perfil);
              aoMudarConta();
            }}
            rodape={
              <form method="post" action="/painel/sair">
                <Botao type="submit" pequeno icone="sys-logout">
                  Sair do painel
                </Botao>
              </form>
            }
          />

          <Secao
            titulo="Espaço de trabalho"
            ajuda="O nome e a sigla aparecem no menu, no lugar de ASIMOV. Serve para reconhecer de qual instalação é a aba aberta."
            campos={[
              { campo: "nome", rotulo: "Nome do espaço", placeholder: "ASIMOV" },
              { campo: "sigla", rotulo: "Sigla, até duas letras", placeholder: "A" },
            ]}
            valores={espaco}
            aoMudar={mudaEspaco}
            rotuloDoBotao="Salvar o espaço"
            aoSalvar={async () => {
              await api.gravaEspaco(espaco);
              aoMudarConta();
            }}
          />

          <Secao
            titulo="Dados do negócio"
            ajuda="De quem opera esta instalação, não das empresas atendidas. Aparecem onde o agente precisa se identificar."
            campos={[
              { campo: "negocio_nome", rotulo: "Razão social ou nome", placeholder: "Estúdio Exemplo ME" },
              { campo: "negocio_documento", rotulo: "CNPJ ou CPF", placeholder: "00.000.000/0000-00" },
              { campo: "negocio_email", rotulo: "E-mail de contato", tipo: "email" },
              { campo: "negocio_telefone", rotulo: "Telefone", placeholder: "com DDD" },
              { campo: "negocio_site", rotulo: "Site", placeholder: "https://" },
            ]}
            valores={espaco}
            aoMudar={mudaEspaco}
            rotuloDoBotao="Salvar os dados"
            aoSalvar={async () => {
              await api.gravaEspaco(espaco);
              aoMudarConta();
            }}
          />

          <AssistenteDeCodigo />
        </div>
      ) : (
        <div className="mt-6">
          <Carregando tipo="pontos" o_que="abrindo as configurações" />
        </div>
      )}
    </>
  );
}
