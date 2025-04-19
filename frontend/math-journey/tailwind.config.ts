// frontend/math-journey/tailwind.config.ts
import type { Config } from 'tailwindcss';

const config: Config = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}', // If using pages router
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}', // Include app router directory
    // Add any other paths that contain Tailwind classes
  ],
  theme: {
    extend: {
      // You can extend your theme here later if needed
      // Example:
      // colors: {
      //   primary: '#yourcolor',
      // },
      backgroundImage: {
        'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
        'gradient-conic': 'conic-gradient(from 180deg at 50% 50%, var(--tw-gradient-stops))',
      },
    },
  },
  plugins: [
    // Add any Tailwind plugins here if you use them
  ],
  darkMode: ["class", "dark"], // Recommended for shadcn-ui if using CSS variables
};

export default config;