/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,jsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'Menlo', 'Monaco', 'monospace'],
      },
      colors: {
        bg: {
          base: '#0a0a0f',
          surface: '#111118',
          elevated: '#16161f',
          mcp: '#0e0e16',
        },
        accent: {
          DEFAULT: '#7c3aed',
          light: '#a78bfa',
          dim: 'rgba(124, 58, 237, 0.15)',
          glow: 'rgba(124, 58, 237, 0.25)',
        },
        border: {
          DEFAULT: 'rgba(255, 255, 255, 0.08)',
          strong: 'rgba(255, 255, 255, 0.14)',
        },
        text: {
          primary: '#ffffff',
          secondary: '#a1a1aa',
          muted: '#52525b',
          dim: '#3f3f46',
        },
      },
      boxShadow: {
        'glow-sm': '0 0 20px rgba(124, 58, 237, 0.2)',
        'glow-md': '0 0 40px rgba(124, 58, 237, 0.25)',
        'glow-lg': '0 0 80px rgba(124, 58, 237, 0.15)',
      },
      backdropBlur: {
        xs: '4px',
      },
    },
  },
  plugins: [],
}
