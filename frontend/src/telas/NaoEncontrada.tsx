import { Link } from "react-router-dom";
import { Botao } from "../design/Botao";

/** Rota que não existe. Ela não pede desculpa, não explica o que houve e oferece a saída. */
export function NaoEncontrada() {
  return (
    <>
      <header className="border-b border-borda pb-6">
        <h1 className="text-2xl font-semibold tracking-tight text-texto">
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
