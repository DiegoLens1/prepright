/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        surface: "#f8f9fa",
        primary: "#1a73e8",
        danger: "#d93025",
        success: "#188038",
        warning: "#f9ab00",
      },
    },
  },
  plugins: [],
};
