/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './shop/templates/**/*.html',
    './shop/**/*.py',
  ],
  theme: {
    extend: {
      colors: {
        champagne: '#EFE6D9',
        'champagne-deep': '#E3D3BD',
        jade: '#1F4A40',
        'jade-light': '#3A6B5E',
        blush: '#E9C9C5',
        maroon: '#5C1F25',
        ink: '#262220',
      },
      fontFamily: {
        serif: ['"Playfair Display"', 'serif'],
        sans: ['Inter', 'sans-serif'],
      },
    },
  },
};
