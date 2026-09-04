'use client'

import * as React from 'react'
import { motion } from 'motion/react'
import { cn } from '@/lib/utils'
import { LabCard } from '@/components/cards/lab-card'
import type { LabCardData } from '@/lib/source'

const list = {
  hidden: {},
  show: {
    transition: { staggerChildren: 0.05 },
  },
}

const item = {
  hidden: { opacity: 0, y: 6, scale: 0.95, filter: 'blur(4px)' },
  show: {
    opacity: 1,
    y: 0,
    scale: 1,
    filter: 'blur(0px)',
    transition: { duration: 0.3, ease: [0.23, 1, 0.32, 1] as const },
  },
}

/* E5 — List entrance. First-view grids resolve once on mount in
   sequence at the stagger token. Never blocks interaction. */
export function LabGrid({
  children,
  className,
}: {
  children: React.ReactNode
  className?: string
}) {
  return (
    <motion.div
      variants={list}
      initial="hidden"
      animate="show"
      className={cn('grid gap-2 sm:grid-cols-2', className)}
    >
      {React.Children.map(children, (child) => (
        <motion.div variants={item}>{child}</motion.div>
      ))}
    </motion.div>
  )
}

/* One mapping from lab pages to cards. Every grid on the site
   renders through here so card content never drifts per surface. */
export function LabCards({ labs }: { labs: LabCardData[] }) {
  return (
    <>
      {labs.map((lab) => (
        <LabCard
          key={lab.url}
          href={lab.url}
          slug={lab.slug}
          title={lab.title}
          description={lab.description}
          track={lab.track}
          difficulty={lab.difficulty}
          port={lab.port}
        />
      ))}
    </>
  )
}
