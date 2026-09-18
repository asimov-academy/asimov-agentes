import { useCallback, useEffect, useState } from "react";
import { Route, Routes } from "react-router-dom";
import {
  api,
  ENTRAR,
  guardaCsrf,
  SemSessao,
  type Empresa,
  type Eu,
} from "./api/cliente";
import { Aviso } from "./design/Aviso";
import { Carregando } from "./design/Carregando";
import { Icone } from "./design/Icone";
import { Casca, type Situacao } from "./telas/Casca";
import { Copiloto } from "./telas/Copiloto";
import { Agentes } from "./telas/Agentes";
import { Canais } from "./telas/Canais";
import { Chat } from "./telas/Chat";
import { Configuracoes } from "./telas/Configuracoes";
import { Contatos } from "./telas/Contatos";
import { Funil } from "./telas/Funil";
import { EmBreve, NaoEncontrada } from "./telas/EmBreve";
import { VisaoGeral } from "./telas/VisaoGeral";

export function App() {
  const [eu, setEu] = useState<Eu | null>(null);
  const [empresas, setEmpresas] = useState<Empresa[]>([]);
  const [empresa, setEmpresa] = useState("");
  const [situacao, setSituacao] = useState<Situacao | null>(null);
  const [erro, setErro] = useState<string>("");
  const [copiloto, setCopiloto] = useState(false);

  const releEu = useCallback(() => {
    api
      .eu()
      .then(setEu)
      .catch(() => undefined);
  }, []);

  useEffect(() => {
    let vivo = true;
    Promise.all([api.eu(), api.empresas()])
      .then(([dados, lista]) => {
        if (!vivo) return;
        guardaCsrf(dados.csrf);
        setEu(dados);
        setEmpresas(lista);
      })
      .catch((problema) => {
        // Sessão vencida volta para o login em vez de mostrar uma tela quebrada.
        if (problema instanceof SemSessao) {
          window.location.assign(ENTRAR);
          return;
        }
        if (vivo) setErro(problema.message);
      });
    return () => {
      vivo = false;
    };
  }, []);

  return (
    <>
      <Casca eu={eu} situacao={situacao}>
        {erro ? (
          <Aviso tom="erro" titulo="não deu para carregar o painel">
            {erro}
          </Aviso>
        ) : !eu ? (
          <Carregando o_que="abrindo o painel" />
        ) : (
          <Routes>
            {/* A situação da barra do topo nasce na Visão geral e fica valendo nas outras telas: é
              uma consulta só, em vez de uma por tela. */}
            <Route
              path="/"
              element={
                <VisaoGeral
                  empresas={empresas}
                  empresa={empresa}
                  aoTrocarEmpresa={setEmpresa}
                  aoSaberSituacao={setSituacao}
                />
              }
            />
            <Route
              path="/agentes"
              element={
                <Agentes
                  empresas={empresas}
                  empresa={empresa}
                  aoTrocarEmpresa={setEmpresa}
                />
              }
            />
            <Route
              path="/agentes/novo"
              element={
                <Agentes
                  empresas={empresas}
                  empresa={empresa}
                  aoTrocarEmpresa={setEmpresa}
                  abrindo="novo"
                />
              }
            />
            <Route
              path="/agentes/:id"
              element={
                <Agentes
                  empresas={empresas}
                  empresa={empresa}
                  aoTrocarEmpresa={setEmpresa}
                />
              }
            />
            <Route
              path="/canais"
              element={
                <Canais
                  empresas={empresas}
                  empresa={empresa}
                  aoTrocarEmpresa={setEmpresa}
                />
              }
            />
            <Route
              path="/chat"
              element={
                <Chat
                  empresas={empresas}
                  empresa={empresa}
                  aoTrocarEmpresa={setEmpresa}
                />
              }
            />
            <Route
              path="/contatos"
              element={
                <Contatos
                  empresas={empresas}
                  empresa={empresa}
                  aoTrocarEmpresa={setEmpresa}
                />
              }
            />
            <Route
              path="/oportunidades"
              element={
                <Funil
                  empresas={empresas}
                  empresa={empresa}
                  aoTrocarEmpresa={setEmpresa}
                />
              }
            />
            <Route
              path="/conhecimento"
              element={<EmBreve titulo="Conhecimento" />}
            />
            <Route
              path="/configuracoes"
              element={<Configuracoes eu={eu} aoMudarConta={releEu} />}
            />
            <Route path="*" element={<NaoEncontrada />} />
          </Routes>
        )}
      </Casca>

      {/* O copiloto acompanha todas as telas, então mora aqui e não dentro de uma delas. O botão
          fica fora do popup para o operador chamá-lo de onde estiver. */}
      {eu && !copiloto && (
        <button
          onClick={() => setCopiloto(true)}
          className="fixed bottom-5 right-5 z-40 flex items-center gap-2 rounded-full border border-ciano/50 bg-panel px-4 py-3 text-sm font-semibold text-ciano shadow-alto transition-colors hover:bg-ciano hover:text-void"
        >
          <Icone nome="comm-chat" tamanho={16} />
          Copiloto
        </button>
      )}
      {copiloto && <Copiloto aoFechar={() => setCopiloto(false)} />}
    </>
  );
}
