// Tailwind config — prefix all classes with `mc-` to avoid host-page collisions.
/** @type {import('tailwindcss').Config} */
export default {
  prefix: "mc-",
  important: ".mc-root",
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  corePlugins: {
    preflight: false,
  },
  theme: {
    extend: {},
  },
  plugins: [],
};
