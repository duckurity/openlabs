import type { MetadataRoute } from 'next'

export const dynamic = 'force-static'

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: 'openlabs',
    short_name: 'openlabs',
    description: 'Open source security labs. Break a real service. Find the flag.',
    start_url: '/',
    scope: '/',
    display: 'standalone',
    background_color: '#1E1E1E',
    theme_color: '#1E1E1E',
    icons: [
      {
        src: '/icon.svg',
        sizes: 'any',
        type: 'image/svg+xml',
        purpose: 'any',
      },
    ],
  }
}
