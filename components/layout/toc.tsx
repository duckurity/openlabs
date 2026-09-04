'use client'

import type * as React from 'react'
import TextScanIcon from '@/components/icons/text-scan'
import { TOCScrollArea } from '@/components/toc'
import { TOCItems } from '@/components/toc/clerk'
import { cn } from '@/lib/utils'

export function TOC({
  className,
  footer,
}: {
  className?: string
  footer?: React.ReactNode
}) {
  return (
    <div
      id="nd-toc"
      className={cn(
        'sticky top-0 flex h-screen gap-1 [grid-area:toc] max-xl:hidden',
        className
      )}
    >
      <div className="flex h-full max-h-screen w-(--fd-toc-width) flex-col gap-1">
        <div className="bg-muted flex max-h-[77vh] min-h-0 flex-col px-6 py-4 font-mono">
          <h3
            id="toc-title"
            className="inline-flex items-center gap-1.5 text-xs font-medium"
          >
            <TextScanIcon className="size-4" />
            <span>On this page</span>
          </h3>
          <TOCScrollArea data-slot="toc-scroll-area" className="scrollbar-none">
            <TOCItems className="[&_a]:text-xs" />
          </TOCScrollArea>
        </div>
        {footer}
        <div className="bg-muted flex-1" />
      </div>
    </div>
  )
}
