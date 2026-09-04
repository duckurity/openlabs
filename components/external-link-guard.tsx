'use client'

import * as React from 'react'
import { Button } from '@/components/ui/button'
import { ArrowUpRightIcon } from '@/components/icons/mini'

type PendingLink = {
  url: string
  host: string
  newTab: boolean
  trigger: HTMLElement | null
}

function isExternalAnchor(el: HTMLAnchorElement): boolean {
  const href = el.getAttribute('href')
  if (!href) return false
  if (el.hasAttribute('download')) return false
  let url: URL
  try {
    url = new URL(href, window.location.href)
  } catch {
    return false
  }
  if (url.protocol !== 'http:' && url.protocol !== 'https:') return false
  return url.origin !== window.location.origin
}

/**
 * Leave-site warning for external links. Intercepts plain left-clicks
 * on off-origin anchors and asks once per click. Modifier clicks,
 * downloads, and same-origin links pass through untouched.
 */
export function ExternalLinkGuard() {
  const [pending, setPending] = React.useState<PendingLink | null>(null)

  React.useEffect(() => {
    function onClick(event: MouseEvent) {
      if (
        event.defaultPrevented ||
        event.button !== 0 ||
        event.metaKey ||
        event.ctrlKey ||
        event.shiftKey ||
        event.altKey
      ) {
        return
      }
      const target = event.target as HTMLElement | null
      const anchor = target?.closest?.('a[href]') as HTMLAnchorElement | null
      if (!anchor || !isExternalAnchor(anchor)) return
      event.preventDefault()
      const url = new URL(
        anchor.getAttribute('href') as string,
        window.location.href
      )
      setPending({
        url: url.href,
        host: url.host,
        newTab: anchor.target === '_blank',
        trigger: anchor,
      })
    }
    document.addEventListener('click', onClick, true)
    return () => document.removeEventListener('click', onClick, true)
  }, [])

  React.useEffect(() => {
    if (!pending) return
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        event.preventDefault()
        close()
      }
    }
    document.addEventListener('keydown', onKeyDown, true)
    return () => document.removeEventListener('keydown', onKeyDown, true)
  }, [pending])

  function close() {
    setPending((current) => {
      current?.trigger?.focus?.()
      return null
    })
  }

  function proceed() {
    if (!pending) return
    const { url, newTab } = pending
    setPending(null)
    if (newTab) {
      window.open(url, '_blank', 'noopener,noreferrer')
    } else {
      window.location.assign(url)
    }
  }

  if (!pending) return null

  return (
    <div
      role="alertdialog"
      aria-modal="true"
      aria-labelledby="leave-site-title"
      aria-describedby="leave-site-detail"
      className="fixed inset-0 z-(--z-dialog) flex items-center justify-center p-4"
    >
      <div
        onClick={close}
        aria-hidden="true"
        className="cctv-backdrop absolute inset-0 cursor-pointer"
      />
      <div className="mount-enter bg-background border-border relative mx-4 flex w-full max-w-md flex-col gap-4 border p-6">
        <h2
          id="leave-site-title"
          className="font-display text-xl leading-tight font-semibold"
        >
          Leaving openlabs
        </h2>
        <p
          id="leave-site-detail"
          className="text-foreground/70 text-sm leading-relaxed"
        >
          This link opens{' '}
          <span className="text-foreground font-medium">{pending.host}</span>.
          Openlabs does not control external sites.
        </p>
        <p className="tnum truncate font-mono text-xs text-muted-foreground">
          {pending.url}
        </p>
        <div className="flex items-center justify-end gap-2">
          <Button variant="ghost" autoFocus onClick={close}>
            Go back
          </Button>
          <Button onClick={proceed}>
            Continue
            <ArrowUpRightIcon className="size-3" />
          </Button>
        </div>
      </div>
    </div>
  )
}
