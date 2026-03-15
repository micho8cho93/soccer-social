/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './futbolapp/templates/**/*.html',
    './futbolapp/**/*.py',
    './config/templates/**/*.html',
    './config/**/*.py',
  ],
  theme: {
    extend: {
      colors: {
        'primary-blue': '#1A55E3',
        'primary-red': '#FF0854',
        'supporting-green': '#00D284',
        'supporting-cyan': '#0DCAF0',
        'supporting-purple': '#5E6EED',
        'grass-green': '#0A8754',
        'pitch-green': '#1A5C3E',
        'goal-yellow': '#FFB800',
        'ink': '#0F3A2A',
        'chalk-white': '#FDFDF8',
        'mist': '#F4F7F3',
        'line-gray': '#D7E0D8',
        'soft-yellow': '#FFF6CF',
        'soft-green': '#EAF6EF',
      },
      fontFamily: {
        display: ['"Bebas Neue"', 'sans-serif'],
        body: ['Antonio', 'sans-serif'],
      },
      boxShadow: {
        competition: '0 24px 60px -28px rgba(15, 58, 42, 0.24)',
        'competition-sm': '0 16px 32px -22px rgba(15, 58, 42, 0.18)',
      },
    },
  },
  plugins: [],
}
