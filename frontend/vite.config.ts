import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

// O painel é servido pela própria API em `/painel/app`, nunca da raiz do domínio: o `base` precisa
// bater com isso, senão o HTML pede o JavaScript em `/assets/...` e leva 404 na VPS.
export default defineConfig({
  base: "/painel/app/",
  plugins: [react()],
  build: { outDir: "dist", emptyOutDir: true, sourcemap: false },
  server: {
    // `npm run dev` na máquina de desenvolvimento fala com a API local; na VPS nada disso existe.
    proxy: { "/painel/api": "http://127.0.0.1:8000" },
  },
  test: {
    environment: "jsdom",
    globals: true,
    include: ["src/**/*.teste.tsx", "src/**/*.teste.ts"],
    css: false,
  },
});
