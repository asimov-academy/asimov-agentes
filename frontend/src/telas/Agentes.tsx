import { useCallback, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api, SemSessao, type Agente, type Empresa, type Situacao } from "../api/cliente";
import { Busca } from "../design/Busca";
import { Segmentos } from "../design/Segmentos";
import { Aviso } from "../design/Aviso";
import { Botao } from "../design/Botao";
import { Cabecalho } from "../design/Cabecalho";
import { Carregando } from "../design/Carregando";
import { Modal } from "../design/Modal";
import { Vazio } from "../design/Vazio";
import { Ficha } from "./agente/Ficha";
import { MenuDeSituacao } from "./agente/MenuDeSituacao";
import { MenuDoAgente } from "./agente/MenuDoAgente";
import { Onboarding } from "./agente/Onboarding";
import { SITUACOES } from "./agente/situacoes";
import { Teste } from "./agente/Teste";

/** A lista de agentes. O popup abre por cima dela, que fica embaçada atrás: é a regra do operador
 *  para toda configuração de agente.
 *
 *  Cada linha diz três coisas e para por aí: quem é o agente (foto e nome), em que situação ele
 *  está e o que ele faz, em qual empresa. Canal e modelo saíram: ninguém escolhe um agente por eles,
 *  e estão na ficha. O resto é o menu de ações, à direita.
 */

/** O que o agente faz, em uma palavra, para a linha da lista. */
const OFICIO: Record<string, string> = {
  atendimento: "Atendente",
  suporte: "Suporte",
  vendas: "Vendedor",
};

const FILTROS: { rotulo: string; valor: Situacao | undefined }[] = [
  { rotulo: "Todos", valor: undefined },
  ...SITUACOES.map((s) => ({ rotulo: s.rotulo, valor: s.valor })),
];

export function Agentes({
  empresas,
  abrindo,
}: {
  /** Só para o onboarding, que escolhe uma: a lista não filtra mais por empresa, e sim pela lupa. */
  empresas: Empresa[];
  /** `novo` abre o onboarding; um id abre a ficha daquele agente. */
  abrindo?: "novo";
}) {
  const [agentes, setAgentes] = useState<Agente[] | null>(null);
  const [situacao, setSituacao] = useState<Situacao | undefined>(undefined);
  // A lupa filtra o que está na tela, e não a consulta: a lista de agentes cabe inteira aqui.
  const [filtro, setFiltro] = useState("");
  const [erro, setErro] = useState("");
  // Quem termina o onboarding escolhendo o que fazer agora cai direto naquela aba da ficha.
  const [abaDaFicha, setAbaDaFicha] = useState<string | undefined>(undefined);
  // Conversar saiu das abas da ficha: é o que se faz o tempo todo, e não uma configuração.
  const [conversando, setConversando] = useState<Agente | null>(null);
  const navega = useNavigate();
  const { id } = useParams();

  const busca = useCallback(() => {
    setErro("");
    api
      .agentes(undefined, situacao)
      .then(setAgentes)
      .catch((problema) => {
        if (problema instanceof SemSessao) throw problema;
        setErro(problema.message);
      });
  }, [situacao]);

  useEffect(busca, [busca]);

  const trocaNaLista = (novo: Agente) =>
    setAgentes((antes) => (antes ?? []).map((outro) => (outro.id === novo.id ? novo : outro)));

  const procurado = filtro.trim().toLowerCase();
  const achados = (agentes ?? []).filter(
    (a) =>
      !procurado ||
      a.nome.toLowerCase().includes(procurado) ||
      a.empresa.toLowerCase().includes(procurado),
  );

  return (
    <>
      {/* A contagem só aparece quando há o que contar: sem agente, quem diz isso é o estado vazio,
          e quem está buscando já tem o carregando embaixo. */}
      <Cabecalho
        titulo="Agentes"
        contexto={
          agentes !== null && achados.length > 0
            ? `${achados.length} ${achados.length === 1 ? "agente" : "agentes"}`
            : undefined
        }
        acoes={
          <>
          <Busca
            valor={filtro}
            aoMudar={setFiltro}
            rotulo="Buscar agente"
            placeholder="nome do agente ou da empresa"
          />

          <Segmentos
            rotulo="Situação"
            opcoes={FILTROS}
            valor={situacao}
            aoMudar={setSituacao}
          />

            <Botao tom="acento" className="min-h-11" icone="act-add" onClick={() => navega("/agentes/novo")}>
              Criar agente
            </Botao>
          </>
        }
      />

      {erro ? (
        <div className="mt-10">
          <Aviso tom="erro" titulo="não deu para carregar os agentes">
            <p>{erro}</p>
            <div className="mt-4">
              <Botao icone="sys-refresh" pequeno onClick={busca}>
                Tentar de novo
              </Botao>
            </div>
          </Aviso>
        </div>
      ) : agentes === null ? (
        <div className="mt-16">
          <Carregando tipo="pontos" o_que="buscando os agentes" />
        </div>
      ) : achados.length === 0 ? (
        <div className="mt-16">
          {procurado ? (
            <Vazio titulo="nenhum agente com esse nome" icone="sys-search">
              Procure pelo nome do agente ou da empresa.
            </Vazio>
          ) : (
            <Vazio titulo="nenhum agente ainda" icone="nav-team">
              Crie o primeiro e converse com ele antes de conectar a um canal.
            </Vazio>
          )}
        </div>
      ) : (
        <ul className="mt-8 flex flex-col gap-1">
          {achados.map((a) => {
            const oficio = OFICIO[a.perfil?.funcao ?? ""];
            return (
              <li
                key={a.id}
                className="flex items-center gap-3 rounded-md px-2 transition-colors hover:bg-surface"
              >
                {/* O avatar é o botão da situação, e fica fora do que abre a ficha: um botão não
                    mora dentro do outro. */}
                <MenuDeSituacao agente={a} aoMudar={trocaNaLista} />

                <button
                  onClick={() => navega(`/agentes/${a.id}`)}
                  className="min-w-0 flex-1 py-3 text-left"
                >
                  <span className="block truncate text-base text-texto">{a.nome}</span>
                  <span className="mt-0.5 block truncate text-sm text-muted">
                    {oficio ? `${oficio} em ${a.empresa}` : a.empresa}
                  </span>
                </button>

                <MenuDoAgente
                  agente={a}
                  aoEditar={() => navega(`/agentes/${a.id}`)}
                  aoConversar={() => setConversando(a)}
                />
              </li>
            );
          })}
        </ul>
      )}

      {conversando && (
        <Modal
          titulo={conversando.nome}
          subtitulo={`Conversa de teste, em ${conversando.empresa}`}
          largura="max-w-3xl"
          aoFechar={() => setConversando(null)}
        >
          <Teste agenteId={conversando.id} agente={conversando.nome} />
        </Modal>
      )}

      {abrindo === "novo" && (
        <Onboarding
          empresas={empresas}
          aoFechar={() => navega("/agentes")}
          aoCriar={(agente, aba) => {
            busca();
            setAbaDaFicha(aba);
            navega(`/agentes/${agente.id}`);
          }}
        />
      )}

      {id && id !== "novo" && (
        <Ficha
          agenteId={id}
          aoFechar={() => {
            setAbaDaFicha(undefined);
            navega("/agentes");
          }}
          aoMudar={busca}
          abaInicial={abaDaFicha as Parameters<typeof Ficha>[0]["abaInicial"]}
        />
      )}
    </>
  );
}
