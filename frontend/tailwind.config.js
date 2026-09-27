/** @type {import('tailwindcss').Config} */
export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: {
          950: "#0B1220",
          900: "#101827",
          800: "#121B2E",
        },
        line: "#1E2A42",
        muted: "#7E8CA6",
        signal: "#33C3A6",
        severity: {
          low: "#3B82F6",
          medium: "#D9A441",
          high: "#E8743B",
          critical: "#E14F4F",
        },
      },
      fontFamily: {
        sans: ["'IBM Plex Sans'", "system-ui", "sans-serif"],
        mono: ["'IBM Plex Mono'", "ui-monospace", "monospace"],
      },
    },
  },
  plugins: [],
};
