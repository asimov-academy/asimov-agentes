import { useCallback, useEffect, useState } from "react";
import {
  api,
  ErroDaApi,
  type EspacoDeTrabalho,
  type Eu,
  type Modelos,
} from "../api/cliente";
import { Aviso } from "../design/Aviso";
import { Botao } from "../design/Botao";
import { Cabecalho } from "../design/Cabecalho";
import { Carregando } from "../design/Carregando";
import { Campo } from "../design/Campo";
import { Cartao } from "../design/Cartao";
import { Icone } from "../design/Icone";
import { Selo } from "../design/Selo";
import { FormDaChave, NOME_DO_PROVEDOR } from "./agente/FormDaChave";

/** Conta, instalação e chaves de IA, no fim do menu.
 *
 *  Nasceu de duas faltas: não havia onde ver a conta do operador nem os endereços da instalação, e
 *  as chaves de IA só apareciam dentro da ficha de um agente, na hora de escolher um modelo. Chave
 *  é da instalação, não do agente, e é aqui que ela se administra.
 */
function data(iso: string | null): string {
  if (!iso) return "nunca";
  return new Date(iso).toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" });
}

function Linha({ rotulo, valor, tecnico }: { rotulo: string; valor: string; tecnico?: boolean }) {
  return (
    <div className="min-w-0">
      <dt className="rotulo">{rotulo}</dt>
      <dd className={`mt-1 truncate text-sm text-texto ${tecnico ? "tecnico" : ""}`} title={valor}>
        {valor}
      </dd>
    </div>
  );
}

/** Um formulário de uma seção: os campos, o botão que salva e o que ele diz depois de salvar. */
function Secao({
  titulo,
  ajuda,
  campos,
  valores,
  aoMudar,
  aoSalvar,
  rotuloDoBotao,
}: {
  titulo: string;
  ajuda?: string;
  campos: { campo: string; rotulo: string; placeholder?: string; tipo?: string }[];
  valores: Record<string, string>;
  aoMudar: (campo: string, valor: string) => void;
  aoSalvar: () => Promise<void>;
  rotuloDoBotao: string;
}) {
  const [salvando, setSalvando] = useState(false);
  const [feito, setFeito] = useState(false);
  const [erro, setErro] = useState("");

  async function salva() {
    setErro("");
    setSalvando(true);
    try {
      await aoSalvar();
      setFeito(true);
      setTimeout(() => setFeito(false), 2500);
    } catch (problema) {
      setErro(problema instanceof ErroDaApi ? problema.message : String(problema));
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
            type={c.tipo}
            placeholder={c.placeholder}
            value={valores[c.campo] ?? ""}
            onChange={(e) => aoMudar(c.campo, e.target.value)}
          />
        ))}
      </div>
      {erro && (
        <Aviso tom="erro" titulo="não deu para salvar">
          <p>{erro}</p>
        </Aviso>
      )}
      <div className="flex items-center gap-3">
        <Botao pequeno icone="act-save" ocupado={salvando} onClick={salva}>
          {rotuloDoBotao}
        </Botao>
        {feito && <Selo tom="ok">salvo</Selo>}
      </div>
    </Cartao>
  );
}

export function Configuracoes({ eu, aoMudarConta }: { eu: Eu | null; aoMudarConta: () => void }) {
  const [modelos, setModelos] = useState<Modelos | null>(null);
  const [espaco, setEspaco] = useState<EspacoDeTrabalho | null>(null);
  const [perfil, setPerfil] = useState<{ nome: string; email: string } | null>(null);
  const [erro, setErro] = useState("");
  const [abrindo, setAbrindo] = useState("");

  const busca = useCallback(() => {
    setErro("");
    api
      .modelos()
      .then(setModelos)
      .catch((problema) => setErro(problema instanceof ErroDaApi ? problema.message : String(problema)));
  }, []);

  useEffect(busca, [busca]);

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
      <Cabecalho titulo="Configurações" contexto="Da instalação inteira, não de um agente." />

      {/* Um cartão, não dois: eram duas metades com quatro linhas cada, e a da direita ficava com
          metade vazia. Saíram também as duas linhas que não diziam nada, "Operador: único desta
          instalação" e um "último acesso" que, com uma conta só, ou é "nunca" ou é "agora". */}

      <div className="mt-6">
        <Cartao titulo="Instalação">
          <dl className="grid gap-x-8 gap-y-4 sm:grid-cols-2 lg:grid-cols-4">
            <Linha rotulo="Painel" valor={eu?.instalacao.subdominio_app || "não publicado"} tecnico />
            <Linha rotulo="Agentes em" valor={eu?.instalacao.subdominio_bot ?? "…"} tecnico />
            <Linha rotulo="Empresas" valor={String(eu?.empresas ?? 0)} />
            <Linha rotulo="Agentes criados" valor={String(eu?.agentes ?? 0)} />
          </dl>

          <div className="flex flex-wrap items-center justify-between gap-4 border-t border-borda pt-4">
            <p className="text-sm text-dim">
              Acesso criado em {data(eu?.operador.criado_em ?? null)}. Para trocar a senha, rode{" "}
              <span className="tecnico text-muted">asimov painel</span> na VPS.
            </p>
            <form method="post" action="/painel/sair">
              <Botao type="submit" pequeno icone="sys-logout">
                Sair do painel
              </Botao>
            </form>
          </div>
        </Cartao>
      </div>

      {espaco && perfil && (
        <div className="mt-4 grid gap-4">
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
            titulo="Perfil do operador"
            ajuda="Quem administra esta instalação. Não serve para entrar: a senha continua a única credencial."
            campos={[
              { campo: "nome", rotulo: "Seu nome", placeholder: "como você quer ser chamado" },
              { campo: "email", rotulo: "Seu e-mail", tipo: "email", placeholder: "para contato, não para entrar" },
            ]}
            valores={perfil}
            aoMudar={(campo, valor) => setPerfil((antes) => (antes ? { ...antes, [campo]: valor } : antes))}
            rotuloDoBotao="Salvar o perfil"
            aoSalvar={async () => {
              await api.gravaPerfilDoOperador(perfil);
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
        </div>
      )}

      <section className="mt-4">
        <Cartao titulo="Chaves de IA">
          <p className="max-w-[70ch] text-sm text-muted">
            Uma chave por provedor, guardada cifrada no servidor e usada por todo agente que escolher
            aquele provedor. Ela entra uma vez e nunca mais sai: aqui só aparece se existe.
          </p>

          {erro ? (
            <Aviso tom="erro" titulo="não deu para carregar os provedores">
              <p>{erro}</p>
              <div className="mt-4">
                <Botao icone="sys-refresh" pequeno onClick={busca}>
                  Tentar de novo
                </Botao>
              </div>
            </Aviso>
          ) : modelos === null ? (
            <Carregando tipo="pontos" o_que="buscando os provedores" />
          ) : (
            <ul className="flex flex-col gap-1">
              {modelos.provedores.map((p) => {
                const tem = modelos.com_chave.includes(p);
                const aberto = abrindo === p;
                return (
                  <li key={p} className="rounded-md border border-borda">
                    <div className="flex flex-wrap items-center justify-between gap-3 px-4 py-3">
                      <span className="flex items-center gap-3">
                        <span className="text-sm text-texto">{NOME_DO_PROVEDOR[p] ?? p}</span>
                        {tem ? <Selo tom="ok">chave guardada</Selo> : <Selo>sem chave</Selo>}
                      </span>
                      <Botao pequeno onClick={() => setAbrindo(aberto ? "" : p)}>
                        {aberto ? "Cancelar" : tem ? "Trocar a chave" : "Guardar a chave"}
                      </Botao>
                    </div>
                    {aberto && (
                      <div className="border-t border-borda px-4 py-4">
                        <div className="max-w-md">
                          <FormDaChave
                            provedor={p}
                            aoGuardar={() => {
                              setAbrindo("");
                              busca();
                            }}
                          />
                        </div>
                      </div>
                    )}
                  </li>
                );
              })}
            </ul>
          )}

          <p className="flex items-start gap-2 text-sm text-dim">
            <Icone nome="stat-info" tamanho={14} className="mt-0.5" />
            Áudio não roda na Anthropic: com ela, guarde também a chave de outro provedor.
          </p>
        </Cartao>
      </section>
    </>
  );
}
