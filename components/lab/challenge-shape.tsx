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
 * show art. Overlay the live Ember wave field on hydrate.
 * Keep the base wash opaque. It carries Ember across the full
 * measure where the dither field stays sparse.
 */
export function ChallengeShape({ slug, className }: ChallengeShapeProps) {
  const [imgFailed, setImgFailed] = React.useState(false)
  const [glFailed, setGlFailed] = React.useState(false)

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
          loading="lazy"
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
          className="absolute inset-0 h-full w-full"
          onError={() => setGlFailed(true)}
        />
      )}
    </span>
  )
}
