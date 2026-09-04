'use client'

import * as React from 'react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { CheckIcon } from '@/components/icons/mini'
import CopyIcon from '@/components/icons/copy'
import { cn } from '@/lib/utils'

/**
 * `hasCopied` flag that auto-resets after `timeout`, shared by the copy hooks.
 */
function useCopiedFlag(timeout = 2000) {
  const [hasCopied, setHasCopied] = React.useState(false)

  React.useEffect(() => {
    if (!hasCopied) return
    const timer = setTimeout(() => setHasCopied(false), timeout)
    return () => clearTimeout(timer)
  }, [hasCopied, timeout])

  return [hasCopied, setHasCopied] as const
}

export function useCopyToClipboard(timeout = 2000) {
  const [hasCopied, setHasCopied] = useCopiedFlag(timeout)

  const copy = React.useCallback(
    async (value: string) => {
      try {
        await navigator.clipboard.writeText(value)
        setHasCopied(true)
        return true
      } catch {
        toast.error('Copy failed. Select the text manually.')
        return false
      }
    },
    [setHasCopied]
  )

  return { hasCopied, copy }
}

export function CopyButton({
  value,
  className,
  successNote,
  ...props
}: {
  value: string
  /** Toast note on success. Empty means morph only, no toast. */
  successNote?: string
} & Omit<
  React.ComponentProps<typeof Button>,
  'children' | 'variant' | 'size' | 'onClick'
>) {
  const { hasCopied, copy } = useCopyToClipboard()

  function handleCopy() {
    void copy(value).then((ok) => {
      if (ok && successNote) toast.success(successNote)
    })
  }

  return (
    <Button
      data-slot="copy-button"
      size="icon"
      variant="ghost"
      className={cn(
        'size-7',
        'absolute top-[0.725rem] right-3 z-10',
        'opacity-0 transition-opacity duration-[var(--duration-fast)] ease-[var(--ease-out)] group-hover/code:opacity-100 hover:opacity-100 focus-visible:opacity-100 has-touch-screen:opacity-100',
        className
      )}
      onClick={handleCopy}
      {...props}
    >
      <span className={cn('icon-swap', hasCopied && 'is-on')}>
        <CopyIcon data-icon="off" className="h-4 w-4" />
        <CheckIcon data-icon="on" className="h-4 w-4" />
      </span>
    </Button>
  )
}
