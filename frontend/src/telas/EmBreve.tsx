import { Link } from "react-router-dom";
import { Botao } from "../design/Botao";
import { Vazio } from "../design/Vazio";

/** A tela do que ainda não existe. Ela diz o que vai fazer e quando, em vez de só "em breve". */
export function EmBreve({ titulo, etapa }: { titulo: string; etapa: string }) {
  return (
    <>
      <header className="border-b border-borda pb-6">
        <h1 className="text-3xl font-semibold tracking-tight text-texto md:text-5xl">
          {titulo}
          <span className="text-ciano">.</span>
        </h1>
        <p className="mt-2 text-sm text-muted">Ainda não construída, e entra na {etapa}.</p>
      </header>

      <div className="mt-10 max-w-[70ch]">
        <p className="text-base leading-relaxed text-texto">
          O agente vai poder responder com base nos seus documentos: você sobe um PDF ou cola um
          texto, e ele passa a citar aquilo em vez de inventar. Cada empresa tem a própria base, e o
          agente só enxerga a dela.
        </p>
        <p className="mt-4 text-sm text-muted">
          Enquanto isso, o que o agente sabe está no prompt dele, na aba Trabalho.
        </p>
        <div className="mt-6">
          <Link to="/agentes">
            <Botao pequeno icone="nav-team">
              Ver os agentes
            </Botao>
          </Link>
        </div>
      </div>
    </>
  );
}

/** Rota que não existe. Ela não pede desculpa e oferece o caminho de volta. */
export function NaoEncontrada() {
  return (
    <>
      <header className="border-b border-borda pb-6">
        <h1 className="text-3xl font-semibold tracking-tight text-texto md:text-5xl">
          Este endereço não existe<span className="text-ciano">.</span>
        </h1>
      </header>
      <div className="mt-10">
        <Vazio titulo="nada aqui" icone="stat-info">
          O endereço pode ter mudado de nome numa versão nova do painel.
        </Vazio>
        <div className="mt-6">
          <Link to="/">
            <Botao pequeno icone="nav-dashboard">
              Ir para a visão geral
            </Botao>
          </Link>
        </div>
      </div>
    </>
  );
}
