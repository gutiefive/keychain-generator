/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx,ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bambu: {
          DEFAULT: "#00FF41",
          dim: "#00cc34",
          glow: "rgba(0, 255, 65, 0.15)",
        },
        carbon: {
          950: "#050505",
          900: "#0a0a0a",
          800: "#121212",
          700: "#1a1a1a",
          600: "#242424",
          500: "#2e2e2e",
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "-apple-system", "sans-serif"],
        mono: ["JetBrains Mono", "Fira Code", "monospace"],
      },
      boxShadow: {
        glow: "0 0 20px rgba(0, 255, 65, 0.25), 0 0 60px rgba(0, 255, 65, 0.1)",
        "glow-sm": "0 0 10px rgba(0, 255, 65, 0.2)",
      },
    },
  },
  plugins: [],
};
