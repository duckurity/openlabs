'use client'

import * as React from 'react'
import dynamic from 'next/dynamic'
import { Logo } from '@/components/logos/logo'
import { cn } from '@/lib/utils'

const DitherWaves = dynamic(
  () =>
    import('@/components/canvasui/dither-waves').then((m) => m.DitherWaves),
  { ssr: false }
)

interface ChallengeShapeProps {
  /** Lab slug, e.g. "duck-cross". Resolves /shapes/<slug>.svg. */
  slug: string
  className?: string
}

/** Deterministic 0..1 seed per slug. Offsets the wave field. */
function seedFromSlug(slug: string): number {
  let hash = 2166136261
  for (let i = 0; i < slug.length; i++) {
    hash ^= slug.charCodeAt(i)
    hash = Math.imul(hash, 16777619)
  }
  return (hash >>> 0) / 4294967295
}

/**
 * Full-bleed dither art, unique per challenge. Paint the seeded
 * shape SVG underneath, so server render and no-JS clients still
 * show art. Overlay the live Ember wave field on hydrate and
 * fade it in on its first frame. Keep the base wash opaque. It
 * carries Ember across the full measure where the dither field
 * stays sparse. Float the mark over the field with luminosity
 * blend, so the glyph borrows the wave hue and sits inside the
 * art instead of stamping over it.
 */
export function ChallengeShape({ slug, className }: ChallengeShapeProps) {
  const [imgFailed, setImgFailed] = React.useState(false)
  const [glFailed, setGlFailed] = React.useState(false)
  const [ready, setReady] = React.useState(false)

  return (
    <span
      className={cn(
        'relative block overflow-hidden bg-[var(--surface-raised)]',
        className
      )}
      aria-hidden="true"
    >
      <span
        aria-hidden="true"
        className="absolute inset-0"
        style={{
          background:
            'linear-gradient(90deg, var(--surface-raised) 0%, color-mix(in oklch, var(--action-500) 24%, var(--surface-raised)) 100%)',
        }}
      />
      {!imgFailed ? (
        /* eslint-disable-next-line @next/next/no-img-element */
        <img
          src={`/shapes/${slug}.svg`}
          alt=""
          loading="eager"
          onError={() => setImgFailed(true)}
          className="absolute inset-0 h-full w-full object-cover"
        />
      ) : (
        <span className="absolute inset-0 flex items-center justify-center bg-card text-foreground">
          <Logo className="size-3/4" />
        </span>
      )}
      {!glFailed && !imgFailed && (
        <DitherWaves
          seed={seedFromSlug(slug)}
          className={cn(
            'absolute inset-0 h-full w-full transition-opacity duration-[var(--duration-slow)] ease-[var(--ease-out)]',
            ready ? 'opacity-100' : 'opacity-0'
          )}
          onError={() => setGlFailed(true)}
          onReady={() => setReady(true)}
        />
      )}
      {!imgFailed && (
        <span className="pointer-events-none absolute inset-0 flex items-center justify-center text-[var(--neutral-950)] mix-blend-luminosity">
          <Logo className="size-8" />
        </span>
      )}
    </span>
  )
}
