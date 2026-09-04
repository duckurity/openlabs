/**
 * Verified badge for lab pages. Sharp dot + sentence-case label,
 * mapped to the site status tokens. Static render, no animation.
 */

import * as React from 'react'
import { cn } from '@/lib/utils'

type LabStatus = 'verified' | 'needs-fix'

const STATUS_CONFIG: Record<
  LabStatus,
  { label: string; dot: string; text: string }
> = {
  verified: {
    label: 'Verified',
    dot: 'bg-(--status-success)',
    text: 'text-(--status-success-strong)',
  },
  'needs-fix': {
    label: 'Needs fix',
    dot: 'bg-(--status-error)',
    text: 'text-(--status-error-strong)',
  },
}

interface StatusIndicatorProps extends Omit<React.ComponentProps<'span'>, 'children'> {
  status: LabStatus
  label?: string
}

function StatusIndicator({ status, label, className, ...props }: StatusIndicatorProps) {
  const config = STATUS_CONFIG[status]
  const displayLabel = label ?? config.label

  return (
    <span
      data-slot="status-indicator"
      data-status={status}
      role="status"
      aria-label={displayLabel}
      className={cn(
        'inline-flex h-8 shrink-0 items-center gap-2 border border-border bg-card px-3 font-mono text-sm whitespace-nowrap',
        config.text,
        className
      )}
      {...props}
    >
      <span
        data-slot="status-dot"
        aria-hidden="true"
        className={cn('size-2 shrink-0', config.dot)}
      />
      <span className="whitespace-nowrap">{displayLabel}</span>
    </span>
  )
}

export { StatusIndicator, type StatusIndicatorProps, type LabStatus }
