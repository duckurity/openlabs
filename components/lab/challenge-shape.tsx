'use client'

import * as React from 'react'
import dynamic from 'next/dynamic'
import { Logo } from '@/components/logos/logo'
import { cn } from '@/lib/utils'

const DitheredObject = dynamic(
  () =>
    import('@/components/canvasui/DitheredObject').then((m) => m.DitheredObject),
  { ssr: false }
)

interface ChallengeShapeProps {
  /** Lab slug, e.g. "duck-cross". Resolves /shapes/<slug>.svg. */
  slug: string
  className?: string
}

/**
 * Animated dithered 3D shape, unique per challenge. Loads three.js
 * lazily on the client only. The static shape SVG always paints
 * underneath, so server render and no-JS clients still show art;
 * the live canvas overlays it on hydrate, or the mark on failure.
 * Keep the base wash opaque. It carries Ember across the full banner
 * where the dither field stays sparse. Keep color in the 3D pass.
 * Grayscale would strip the Ember peak from the shape.
 */
export function ChallengeShape({ slug, className }: ChallengeShapeProps) {
  const [failed, setFailed] = React.useState(false)

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
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={`/shapes/${slug}.svg`}
        alt=""
        loading="lazy"
        className="absolute inset-0 h-full w-full object-cover"
      />
      {!failed ? (
        <DitheredObject
          src={`/shapes/${slug}.svg`}
          method="bayer"
          gridSize={4}
          grayscale={false}
          // Ember mirrors var(--action-500). The 3D engine needs hex.
          highlight="#FF3616"
          orbit={false}
          zoom={false}
          autoRotate
          autoRotateSpeed={1}
          floatIntensity={1}
          rotationIntensity={1}
          className="absolute inset-0 h-full w-full"
          onError={() => setFailed(true)}
        />
      ) : (
        <span className="absolute inset-0 flex items-center justify-center bg-card text-foreground">
          <Logo className="size-3/4" />
        </span>
      )}
    </span>
  )
}
