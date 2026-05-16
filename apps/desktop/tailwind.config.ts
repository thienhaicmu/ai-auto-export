import type { Config } from 'tailwindcss'

export default {
  content: ['./src/**/*.{ts,tsx,html}'],
  theme: {
    extend: {
      colors: {
        // Design tokens from ARCHITECTURE.md §9
        'app':          '#0A0A0B',
        'panel':        '#111114',
        'elevated':     '#17171B',
        'subtle':       '#1F1F25',
        'strong':       '#2A2A33',
        'primary':      '#F5F5F7',
        'secondary':    '#9B9BA8',
        'muted':        '#5E5E6E',
        'accent':       '#7C5CFF',
        'success':      '#34D399',
        'warn':         '#F59E0B',
        'error':        '#F87171',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Menlo', 'monospace'],
      },
      fontSize: {
        '2xs': '11px',
        'xs':  '12px',
        'sm':  '13px',
        'base': '14px',
        'lg':  '16px',
        'xl':  '20px',
        '2xl': '28px',
      },
      transitionTimingFunction: {
        'cinematic': 'cubic-bezier(0.22, 1, 0.36, 1)',
      },
      transitionDuration: {
        DEFAULT: '200ms',
        'slow':  '280ms',
      },
      borderColor: {
        DEFAULT: '#1F1F25',
      },
      ringColor: {
        DEFAULT: '#7C5CFF',
      },
    },
  },
  plugins: [],
} satisfies Config
