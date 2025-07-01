/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      keyframes: {
        shimmer: {
          '100%': {
            transform: 'translateX(100%)',
          },
        },
      },
      animation: {
        shimmer: 'shimmer 2s infinite',
      },
      borderRadius: {
        xl: "1rem",
        "2xl": "1.5rem",
        "3xl": "2rem",
      },
      colors: {
        primary: {
          50: "#f8fafc",
          100: "#f1f5f9",
          200: "#e2e8f0",
          300: "#cbd5e1",
          400: "#94a3b8",
          500: "#64748b",
          600: "#475569",
          700: "#334155",
          800: "#1e293b",
          900: "#0f172a",
        },
        dark: {
          DEFAULT: "#0F172A",
          light: "#1E293B",
          lighter: "#334155",
          dark: "#020617",
        },
        accent: {
          blue: "#3B82F6",
          indigo: "#6366F1",
          purple: "#8B5CF6",
          pink: "#EC4899",
        },
      },
      padding: {
        safe: "env(safe-area-inset-bottom)",
      },
      zIndex: {
        60: "60",
      },
    },
  },
  plugins: [],
};
