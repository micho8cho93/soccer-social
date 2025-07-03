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
      },
    },
  },
  plugins: [],
}
