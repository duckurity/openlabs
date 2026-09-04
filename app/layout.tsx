import './styles/globals.css'
import type { Metadata, Viewport } from 'next'
import { Funnel_Display, Geist, Geist_Mono } from 'next/font/google'
import { RootProvider } from 'fumadocs-ui/provider/next'
import { MotionConfig } from 'motion/react'
import { Toaster } from 'sonner'
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
  openGraph: {
    siteName: 'openlabs',
    type: 'website',
  },
  twitter: {
    card: 'summary_large_image',
  },
}

export const viewport: Viewport = {
  maximumScale: 1,
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
          {children}
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
