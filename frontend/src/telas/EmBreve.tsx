import { Link } from "react-router-dom";
import { Botao } from "../design/Botao";

/** A tela do que ainda não existe: uma linha do que vai fazer e o que dá para usar hoje.
 *
 *  A fase do plano não vai para a tela: "Fase 6" é
 *  nome do nosso plano, e não diz nada a quem está no painel (auditoria de copy de 2026-09-18).
 */
export function EmBreve({ titulo }: { titulo: string }) {
  return (
    <>
      <header className="border-b border-borda pb-6">
        <h1 className="text-3xl font-semibold tracking-tight text-texto md:text-5xl">
          {titulo}
          <span className="text-ciano">.</span>
        </h1>
        <p className="mt-2 text-sm text-muted">Ainda não construída.</p>
      </header>

      <div className="mt-10 max-w-[70ch]">
        <p className="text-base leading-relaxed text-texto">
          O agente vai poder responder com base nos seus documentos, em vez de só com o prompt.
        </p>
        <p className="mt-4 text-sm text-muted">
          Por enquanto, o que ele sabe está no prompt dele, na aba Trabalho.
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

/** Rota que não existe. Ela não pede desculpa, não explica o que houve e oferece a saída. */
export function NaoEncontrada() {
  return (
    <>
      <header className="border-b border-borda pb-6">
        <h1 className="text-3xl font-semibold tracking-tight text-texto md:text-5xl">
          Este endereço não existe<span className="text-ciano">.</span>
        </h1>
      </header>
      <div className="mt-10">
        <Link to="/">
          <Botao pequeno icone="nav-dashboard">
            Ir para a visão geral
          </Botao>
        </Link>
      </div>
    </>
  );
}
