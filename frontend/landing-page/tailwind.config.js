/** Algolia brand tokens (Nebula Blue, ink, Sora). */
export default {
  darkMode: ["selector", '[data-theme="dark"]'],
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        algolia: { DEFAULT: "#003DFF", 700: "#0031cc", 300: "#4d77ff", 100: "#e6ecff", 50: "#f2f5ff" },
        ink: "#021046",
      },
      fontFamily: { sora: ["Sora", "system-ui", "sans-serif"] },
    },
  },
  plugins: [],
};
