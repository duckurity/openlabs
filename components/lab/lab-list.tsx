'use client'

import { LabGrid, LabCards } from '@/components/lab/lab-grid'
import type { LabCardData } from '@/lib/source'
import FlaskIcon from '@/components/icons/flask'

export function LabList({ labs }: { labs: LabCardData[] }) {
  if (labs.length === 0) {
    return (
      <div className="text-muted-foreground flex h-full flex-col items-center justify-center gap-3 [grid-area:main]">
        <div className="hatch h-8 w-32" aria-hidden="true" />
        <FlaskIcon className="size-8" />
        <p className="font-mono text-sm tracking-wide">
          No labs yet
        </p>
        <p className="text-muted-foreground/70 text-sm">
          New labs ship with each release. Check back soon.
        </p>
      </div>
    )
  }

  return (
    <LabGrid className="mt-10">
      <LabCards labs={labs} />
    </LabGrid>
  )
}
