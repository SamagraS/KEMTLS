import type { Config } from "tailwindcss";
import tailwindcssAnimate from "tailwindcss-animate";

export default {
  darkMode: ["class"],
  content: ["./pages/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./app/**/*.{ts,tsx}", "./src/**/*.{ts,tsx}"],
  prefix: "",
  theme: {
    extend: {
      fontFamily: {
        display: ['Orbitron', 'sans-serif'],
        body: ['Rajdhani', 'sans-serif'],
        code: ['JetBrains Mono', 'monospace'],
      },
      colors: {
        void: '#020614',
        abyss: '#060d1f',
        deep: '#0a1628',
        panel: '#0d1b2e',
        surface: '#112240',
        raised: '#1a3050',
        cyan: '#00e5ff',
        magenta: '#ff00e5',
        electric: '#4d7dff',
        lime: '#39ff14',
        amber: '#ffab00',
        red: '#ff1744',
        teal: '#1de9b6',
        violet: '#b388ff',
      },
      borderRadius: {
        lg: "0.5rem",
        md: "0.375rem",
        sm: "0.25rem",
      },
      keyframes: {
        "glow-breathe": {
          "0%, 100%": { boxShadow: "0 0 5px currentColor, 0 0 10px currentColor" },
          "50%": { boxShadow: "0 0 10px currentColor, 0 0 30px currentColor, 0 0 60px currentColor" },
        },
        shimmer: {
          "0%": { transform: "translateX(-100%)" },
          "100%": { transform: "translateX(200%)" },
        },
        "pulse-glow": {
          "0%, 100%": { opacity: "0.6" },
          "50%": { opacity: "1" },
        },
        scan: {
          "0%": { top: "-2px" },
          "100%": { top: "100%" },
        },
        float: {
          "0%, 100%": { transform: "translateY(0px)" },
          "50%": { transform: "translateY(-8px)" },
        },
        "hex-rotate": {
          "0%": { transform: "rotate(0deg)" },
          "100%": { transform: "rotate(360deg)" },
        },
      },
      animation: {
        "glow-breathe": "glow-breathe 2s ease infinite",
        shimmer: "shimmer 2s ease-in-out infinite",
        "pulse-glow": "pulse-glow 1s ease infinite",
        scan: "scan 1.5s linear infinite",
        float: "float 4s ease-in-out infinite",
        "hex-rotate": "hex-rotate 8s linear infinite",
      },
    },
  },
  plugins: [tailwindcssAnimate],
} satisfies Config;
