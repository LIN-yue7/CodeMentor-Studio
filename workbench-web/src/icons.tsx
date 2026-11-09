import type { CSSProperties } from 'react'

const paths = {
  code: 'm8 5-6 7 6 7m8-14 6 7-6 7m-3-16-2 18',
  scan: 'M8 3H3v5m13-5h5v5M3 16v5h5m13-5v5h-5M7 12h10m-5-5v10',
  terminal: 'm5 7 4 5-4 5m7 0h7M3 3h18v18H3z',
  chart: 'M4 20V11m8 9V4m8 16v-7',
  folder: 'M3 5h6l2 3h10v12H3z',
  shield: 'M12 2 3 6v6c0 5 9 10 9 10s9-5 9-10V6zM8 12l3 3 5-6',
  play: 'm8 4 12 8-12 8z',
  book: 'M12 5c-3-2-6-2-10-1v15c4-1 7-1 10 1 3-2 6-2 10-1V4c-4-1-7-1-10 1zm0 0v15',
  arrow: 'M4 12h16m-6-6 6 6-6 6',
} as const

export function Icon({ name, style }: { name: keyof typeof paths; style?: CSSProperties }) {
  return <svg className="icon" style={style} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d={paths[name]} /></svg>
}
