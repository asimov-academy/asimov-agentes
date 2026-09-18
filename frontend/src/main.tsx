import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { App } from "./App";
import "./estilos.css";

// O painel mora em `/painel/app`: o router precisa saber, senão toda rota interna vira 404 do Caddy.
createRoot(document.getElementById("raiz")!).render(
  <StrictMode>
    <BrowserRouter basename="/painel/app">
      <App />
    </BrowserRouter>
  </StrictMode>,
);
