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
 */
export function ChallengeShape({ slug, className }: ChallengeShapeProps) {
  const [failed, setFailed] = React.useState(false)

  return (
    <span className={cn('relative block overflow-hidden', className)} aria-hidden="true">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={`/shapes/${slug}.svg`}
        alt=""
        loading="lazy"
        className="absolute inset-0 h-full w-full"
      />
      {!failed ? (
        <DitheredObject
          src={`/shapes/${slug}.svg`}
          method="bayer"
          gridSize={4}
          grayscale
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
