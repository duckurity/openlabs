import * as React from 'react'

import { cn } from '@/lib/utils'

/* The site renders one badge: accent fill, sliced corners. */

function Badge({ className, ...props }: React.ComponentProps<'span'>) {
  return (
    <span
      data-slot="badge"
      className={cn(
        'focus-ring inline-flex items-center justify-center border border-transparent bg-accent font-medium text-accent-foreground w-fit whitespace-nowrap shrink-0 gap-1 overflow-hidden font-mono tracking-wide transition-[color,box-shadow] duration-[var(--duration-fast)] ease-[var(--ease-out)] px-2.5 py-1 text-xs [clip-path:polygon(6px_0%,100%_0%,100%_calc(100%-6px),calc(100%-6px)_100%,0%_100%,0%_6px)]',
        className
      )}
      {...props}
    />
  )
}

export { Badge }
