import type { Config } from 'tailwindcss'

export default {
  content: [
    './src/**/*.{js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        bg: '#F7E7D3',
        ink: '#121212',
        panel: '#FBEEDB',
        accent: '#F4B73B',
        mint: '#C8F3D9',
        rose: '#FFD1D9',
      },
      boxShadow: {
        ink: '0 2px 0 #121212',
      },
      borderWidth: {
        ink: '2px',
      },
    },
  },
  plugins: [],
} satisfies Config

