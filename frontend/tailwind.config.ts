import type { Config } from "tailwindcss";

// Os valores vêm do design system em `designsystem/` (projeto "Enterprise SaaS UI") e existem só
// aqui. Tela e componente usam o nome do token, nunca o hexadecimal: um teste confere isso.
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        void: "#000000",
        surface: "#0a0a0a",
        panel: "#111111",
        borda: "#222222",
        // A escala de texto vai de 15:1 a 5,5:1 sobre os três fundos, toda ela acima dos 4,5:1
        // que a WCAG AA pede. `dim` (#444) e `muted` (#525252) ficavam em 1,9:1 e 2,4:1: rótulo
        // de campo e texto de apoio sumiam no preto. `dim` também é borda de campo e trilho de
        // interruptor, que pedem 3:1 por serem componente.
        dim: "#8a8a8a",
        muted: "#a3a3a3",
        texto: "#e5e5e5",
        ciano: "#29b8db",
        ok: "#00cc66",
        atencao: "#ffaa00",
        perigo: "#ff453a",
        // A régua do gráfico da AXIS (seção 2, `.grid-line`), mais clara que a borda do cartão.
        grade: "#262626",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "ui-monospace", "monospace"],
      },
      borderRadius: { none: "0" },
      // O brilho do arco do medidor e do foco, no valor do design system. Fica aqui para nenhuma
      // tela precisar escrever a cor solta.
      dropShadow: { ciano: "0 0 5px rgba(41, 184, 219, 0.5)" },
      boxShadow: { ativo: "0 0 10px rgba(229, 229, 229, 0.3)" },
      // As três animações da AXIS e do KINETIC (seções 2 e 3): a linha que se desenha, a barra que
      // cresce de baixo para cima e o ponto que aparece depois dela. Duração e curva são as do
      // original; quem prefere menos movimento recebe o resultado final na hora, pelo `estilos.css`.
      keyframes: {
        traco: { to: { strokeDashoffset: "0" } },
        cresce: { to: { transform: "scaleY(1)" } },
        surge: { to: { opacity: "1" } },
        entra: { from: { opacity: "0", transform: "translateY(0.5rem)" }, to: { opacity: "1", transform: "translateY(0)" } },
        // Os dois do KINETIC (seção 3): o radar do Pulse e o traço que corre do Ring.
        radar: {
          "0%": { transform: "scale(0.5)", opacity: "1", borderWidth: "2px" },
          "100%": { transform: "scale(2.5)", opacity: "0", borderWidth: "0px" },
        },
        anel: {
          "0%": { strokeDasharray: "1, 200", strokeDashoffset: "0" },
          "50%": { strokeDasharray: "90, 200", strokeDashoffset: "-35px" },
          "100%": { strokeDasharray: "90, 200", strokeDashoffset: "-124px" },
        },
      },
      animation: {
        traco: "traco 1.5s cubic-bezier(0.16, 1, 0.3, 1) forwards",
        cresce: "cresce 1s cubic-bezier(0.16, 1, 0.3, 1) forwards",
        surge: "surge 1s ease forwards",
        entra: "entra 0.4s cubic-bezier(0.16, 1, 0.3, 1) both",
        radar: "radar 2s infinite",
        anel: "anel 1.5s ease-in-out infinite",
      },
    },
  },
  plugins: [],
} satisfies Config;
