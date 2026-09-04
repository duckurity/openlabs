/**
 * License badge. Shows an SPDX identifier with a category tag and
 * an OSI-approved indicator. Static render, no API call.
 *
 * Adapted to the site brand: sharp corners, no shadows, Phosphor
 * Bold icons, status-token category colors, sentence-case labels.
 */

import * as React from 'react'
import { cn } from '@/lib/utils'
import FileIcon from '@/components/icons/file'
import { CheckIcon, ArrowUpRightIcon } from '@/components/icons/mini'
import { resolveLicense, CATEGORY_CONFIG } from '@/lib/licenses'

interface LicenseBadgeProps extends Omit<React.ComponentProps<'a'>, 'children' | 'href'> {
  /** SPDX license identifier (e.g. "Apache-2.0"). */
  license: string
  /** Show license category tag. @default false */
  showCategory?: boolean
  /** Show OSI-approved indicator. @default true */
  showOsi?: boolean
  /** URL to link to. Defaults to the license text URL. */
  href?: string
}

function LicenseBadge({
  license,
  showCategory = false,
  showOsi = true,
  href: hrefProp,
  className,
  ...props
}: LicenseBadgeProps) {
  const info = resolveLicense(license)
  const href = hrefProp ?? info.url
  const category = CATEGORY_CONFIG[info.category]

  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      data-slot="license-badge"
      data-category={info.category}
      aria-label={`${info.name}${info.osiApproved ? ' — OSI approved' : ''}`}
      className={cn(
        'focus-ring inline-flex h-8 shrink-0 items-center gap-2 border border-border bg-muted/50 px-3 font-mono text-sm whitespace-nowrap text-muted-foreground transition-colors outline-none hover:bg-accent hover:text-accent-foreground [&_svg]:size-4',
        className
      )}
      {...props}
    >
      <FileIcon className="shrink-0" />
      <span>{info.spdxId}</span>
      {showOsi && info.osiApproved && (
        <span className="inline-flex items-center gap-1 opacity-60">
          <CheckIcon className="size-3 shrink-0" />
          <span className="text-xs">OSI</span>
        </span>
      )}
      {showCategory && (
        <span
          className={cn(
            'inline-flex items-center px-1.5 py-0.5 font-mono text-[10px] leading-none',
            category.className
          )}
        >
          {category.label}
        </span>
      )}
      <ArrowUpRightIcon className="size-3 shrink-0 opacity-50" />
    </a>
  )
}

export { LicenseBadge, type LicenseBadgeProps }
