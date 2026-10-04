/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        bg: "#0a0a0f",
        "bg-subtle": "#12121a",
        card: "#1a1a24",
        "card-hover": "#22222d",
        fg: "#e8e8f0",
        muted: "#6b6b80",
        accent: "#00d4aa",
        error: "#ff4757",
        warning: "#ffa502",
        border: "#2a2a3a",
      },
      borderRadius: {
        radius: "8px",
      },
    },
  },
  plugins: [],
}