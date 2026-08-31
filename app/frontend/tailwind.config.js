/** @type {import('tailwindcss').Config} */
export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{vue,js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        monokai: {
          // Dark Mode Palette
          bg: "#272822",
          panel: "#1e1e19",
          card: "#32332d",
          border: "#44433b",
          fg: "#f8f8f2",
          muted: "#b0b0a8",
          yellow: "#e6db74",
          pink: "#f92672",
          cyan: "#66d9ef",
          green: "#a6e22e",
          purple: "#ae81ff",
          orange: "#fd971f",
          // Light Mode Palette
          "light-bg": "#faf8f5",
          "light-panel": "#f2efe9",
          "light-card": "#ffffff",
          "light-border": "#e5e0d5",
          "light-fg": "#2d2a2e",
          "light-muted": "#787670",
          "light-cyan": "#0284c7",
          "light-pink": "#d62662",
          "light-green": "#16a34a",
          "light-yellow": "#ca8a04",
        },
      },
    },
  },
  plugins: [require("@tailwindcss/typography")],
};
