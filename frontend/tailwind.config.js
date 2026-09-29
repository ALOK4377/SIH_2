/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        paper: "#F4F6F9",
        surface: "#FFFFFF",
        hairline: "#DCE3ED",
        ink: {
          DEFAULT: "#12233D", // navy spine
          soft: "#1B3255",
        },
        steel: {
          DEFAULT: "#5A6B82",
          light: "#8A97A9",
        },
        // meaning-encoded accents
        verified: {
          DEFAULT: "#0E7C66", // harmonized / approved
          soft: "#E3F1ED",
        },
        attention: {
          DEFAULT: "#E0A32E", // duplicate / needs attention
          soft: "#FBF0D9",
        },
        conflict: {
          DEFAULT: "#C0453B", // spec conflict / rejected
          soft: "#F7E4E2",
        },
      },
      fontFamily: {
        display: ['"Space Grotesk"', "system-ui", "sans-serif"],
        sans: ['"Inter"', "system-ui", "sans-serif"],
        mono: ['"IBM Plex Mono"', "ui-monospace", "monospace"],
      },
      boxShadow: {
        card: "0 1px 2px rgba(18,35,61,0.04), 0 1px 3px rgba(18,35,61,0.06)",
        lift: "0 4px 16px rgba(18,35,61,0.10)",
      },
      borderRadius: {
        xl: "0.875rem",
      },
    },
  },
  plugins: [],
};
