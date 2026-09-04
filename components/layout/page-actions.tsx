'use client'

import * as React from 'react'
import { CheckIcon } from '@/components/icons/mini'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Kbd } from '@/components/ui/kbd'
import CopyIcon from '@/components/icons/copy'
import { useCopyToClipboard } from '@/components/copy-button'

export function PageActions({
  content,
  className,
}: {
  content: string
  className?: string
}) {
  const { hasCopied, copy } = useCopyToClipboard()

  React.useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      const modifier = event.metaKey || event.ctrlKey
      if (!modifier || event.key.toLowerCase() !== 'u') return
      const target = event.target as HTMLElement | null
      const typing =
        target instanceof HTMLInputElement ||
        target instanceof HTMLTextAreaElement ||
        target?.isContentEditable
      if (typing) return
      event.preventDefault()
      copy(content)
    }
    document.addEventListener('keydown', onKeyDown)
    return () => document.removeEventListener('keydown', onKeyDown)
  }, [content, copy])

  return (
    <div className={cn('not-prose flex items-center gap-1', className)}>
      <Button
        variant="secondary"
        size="sm"
        className="gap-x-2 font-mono tracking-wide"
        onClick={() => copy(content)}
      >
        <span className={cn('icon-swap', hasCopied && 'is-on')}>
          <CopyIcon data-icon="off" className="size-4" />
          <CheckIcon data-icon="on" className="size-4" />
        </span>
        {hasCopied ? (
          <>
            Copied!
          </>
        ) : (
          <>
            Copy page
            <Kbd className="font-normal">⌘U</Kbd>
          </>
        )}
      </Button>
    </div>
  )
}
