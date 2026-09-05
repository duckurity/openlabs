import './styles/globals.css'
import type { Metadata, Viewport } from 'next'
import { Funnel_Display, Geist, Geist_Mono } from 'next/font/google'
import { RootProvider } from 'fumadocs-ui/provider/next'
import { MotionConfig } from 'motion/react'
import { Toaster } from 'sonner'
import { ExternalLinkGuard } from '@/components/external-link-guard'
import { cn } from '@/lib/utils'
import { APP_BASE_URL } from '@/lib/constants'

const funnelDisplay = Funnel_Display({
  subsets: ['latin'],
  variable: '--font-display',
  weight: ['400', '500', '600', '700'],
})

const geist = Geist({
  subsets: ['latin'],
  variable: '--font-body',
})

const geistMono = Geist_Mono({
  subsets: ['latin'],
  variable: '--font-mono',
})

export const metadata: Metadata = {
  metadataBase: new URL(APP_BASE_URL),
  title: {
    template: '%s | openlabs',
    default: 'openlabs',
  },
  description:
    'Open source security labs. Break a real service. Find the flag.',
  authors: [{ name: 'openlabs', url: APP_BASE_URL }],
  creator: 'openlabs',
  publisher: 'openlabs',
  openGraph: {
    siteName: 'openlabs',
    type: 'website',
    locale: 'en_US',
    images: [
      {
        url: '/opengraph-image.png',
        width: 1200,
        height: 630,
        alt: 'openlabs',
      },
    ],
  },
  twitter: {
    card: 'summary_large_image',
    images: ['/opengraph-image.png'],
  },
}

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  themeColor: [
    { media: '(prefers-color-scheme: light)', color: '#F4F2F1' },
    { media: '(prefers-color-scheme: dark)', color: '#1E1E1E' },
  ],
}

export default function Layout({ children }: LayoutProps<'/'>) {
  return (
    <html
      lang="en"
      className={cn(funnelDisplay.variable, geist.variable, geistMono.variable)}
      suppressHydrationWarning
    >
      <body className={cn('font-body antialiased')}>
        <RootProvider
          search={{
            enabled: false,
          }}
          theme={{
            themes: ['light', 'dark'],
            defaultTheme: 'dark',
          }}
        >
        <MotionConfig reducedMotion="user">
          <meta
            name="referrer"
            content="strict-origin-when-cross-origin"
          />
          <meta
            httpEquiv="Content-Security-Policy"
            content="default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' blob: data: https://avatars.githubusercontent.com https://github.com; font-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'self'; form-action 'none'; frame-src 'none'; worker-src 'none'; upgrade-insecure-requests"
          />
          {children}
          <ExternalLinkGuard />
          <Toaster
            position="top-right"
            toastOptions={{
              duration: 4000,
              style: {
                background: 'var(--surface-raised)',
                color: 'var(--text-primary)',
                border: '1px solid var(--line-default)',
                borderRadius: 0,
                fontFamily: 'var(--font-mono)',
                fontSize: 12,
              },
            }}
          />
        </MotionConfig>
        </RootProvider>
      </body>
    </html>
  )
}
