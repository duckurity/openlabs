'use client'

import {
  type ComponentProps,
  createContext,
  type ReactNode,
  useMemo,
} from 'react'
import { cn } from '@/lib/utils'
import { useIsScrollTop } from 'fumadocs-ui/utils/use-is-scroll-top'

const LayoutContext = createContext<{
  isNavTransparent: boolean
} | null>(null)

export function LayoutContextProvider({
  navTransparentMode = 'none',
  children,
}: {
  navTransparentMode?: 'always' | 'top' | 'none'
  children: ReactNode
}) {
  const isTop =
    useIsScrollTop({ enabled: navTransparentMode === 'top' }) ?? true
  const isNavTransparent =
    navTransparentMode === 'top' ? isTop : navTransparentMode === 'always'

  return (
    <LayoutContext
      value={useMemo(
        () => ({
          isNavTransparent,
        }),
        [isNavTransparent]
      )}
    >
      {children}
    </LayoutContext>
  )
}

export function LayoutBody({
  className,
  style,
  children,
  ...props
}: ComponentProps<'div'>) {
  return (
    <div
      id="nd-docs-layout"
      className={cn(
        'grid min-h-(--fd-docs-height) auto-cols-auto auto-rows-auto overflow-x-clip [--fd-docs-height:100dvh] [--fd-header-height:0px] [--fd-sidebar-width:0px] [--fd-toc-popover-height:0px] [--fd-toc-width:0px]',
        className
      )}
      style={
        {
          gridTemplate: `"sidebar header toc"
        "sidebar toc-popover toc"
        "sidebar main toc" 1fr / minmax(var(--fd-sidebar-width), 1fr) minmax(0, calc(var(--fd-layout-width) - var(--fd-sidebar-width) - var(--fd-toc-width))) minmax(min-content, 1fr)`,
          '--fd-docs-row-1': 'var(--fd-banner-height, 0px)',
          '--fd-docs-row-2':
            'calc(var(--fd-docs-row-1) + var(--fd-header-height))',
          '--fd-docs-row-3':
            'calc(var(--fd-docs-row-2) + var(--fd-toc-popover-height))',
          ...style,
        } as object
      }
      {...props}
    >
      {children}
    </div>
  )
}
