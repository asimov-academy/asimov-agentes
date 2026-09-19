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
import { Casca, type Situacao } from "./telas/Casca";
import { Copiloto } from "./telas/Copiloto";
import { Agentes } from "./telas/Agentes";
import { Canais } from "./telas/Canais";
import { Chat } from "./telas/Chat";
import { Configuracoes } from "./telas/Configuracoes";
import { Contatos } from "./telas/Contatos";
import { Funil } from "./telas/Funil";
import { NaoEncontrada } from "./telas/NaoEncontrada";
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
      <Casca
        eu={eu}
        situacao={situacao}
        copilotoAberto={copiloto}
        aoAbrirCopiloto={eu ? () => setCopiloto(true) : undefined}
        // O copiloto acompanha todas as telas, então mora aqui e não dentro de uma delas.
        copiloto={copiloto && eu ? <Copiloto aoFechar={() => setCopiloto(false)} /> : undefined}
      >
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
                <Agentes empresas={empresas} />
              }
            />
            <Route
              path="/agentes/novo"
              element={
                <Agentes empresas={empresas} abrindo="novo" />
              }
            />
            <Route
              path="/agentes/:id"
              element={
                <Agentes empresas={empresas} />
              }
            />
            <Route
              path="/canais"
              element={
                <Canais />
              }
            />
            <Route
              path="/chat"
              element={
                <Chat />
              }
            />
            <Route
              path="/contatos"
              element={
                <Contatos />
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
              path="/configuracoes"
              element={<Configuracoes eu={eu} aoMudarConta={releEu} />}
            />
            <Route path="*" element={<NaoEncontrada />} />
          </Routes>
        )}
      </Casca>

    </>
  );
}
