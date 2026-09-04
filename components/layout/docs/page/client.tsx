'use client'

import {
  type ComponentProps,
  createContext,
  use,
  useEffect,
  useEffectEvent,
  useMemo,
  useRef,
  useState,
} from 'react'
import CaretDownIcon from '@/components/icons/caret-down'
import { cn } from '@/lib/utils'
import { useI18n } from 'fumadocs-ui/contexts/i18n'
import { useTreePath } from 'fumadocs-ui/contexts/tree'
import { useTOCItems } from '../../../toc'
import { useActiveAnchor } from 'fumadocs-core/toc'

const TocPopoverContext = createContext<{
  open: boolean
  setOpen: (open: boolean) => void
} | null>(null)

export function PageTOCPopover({
  className,
  children,
  ...rest
}: ComponentProps<'div'>) {
  const ref = useRef<HTMLElement>(null)
  const [open, setOpen] = useState(false)

  const onClick = useEffectEvent((e: Event) => {
    if (!open) return

    if (ref.current && !ref.current.contains(e.target as HTMLElement))
      setOpen(false)
  })

  useEffect(() => {
    window.addEventListener('click', onClick)

    return () => {
      window.removeEventListener('click', onClick)
    }
  }, [])

  return (
    <TocPopoverContext
      value={useMemo(
        () => ({
          open,
          setOpen,
        }),
        [setOpen, open]
      )}
    >
      <div
        data-toc-popover=""
        data-state={open ? 'open' : 'closed'}
        className={cn(
          'max-xl:layout:[--fd-toc-popover-height:--spacing(10)] sticky top-(--fd-docs-row-2) z-(--z-toc-popover) h-(--fd-toc-popover-height) [grid-area:toc-popover] xl:hidden',
          className
        )}
        {...rest}
      >
        <header ref={ref} className="bg-background font-mono">
          {children}
        </header>
      </div>
    </TocPopoverContext>
  )
}

export function PageTOCPopoverTrigger({
  className,
  ...props
}: ComponentProps<'button'>) {
  const { text } = useI18n()
  const { open, setOpen } = use(TocPopoverContext)!
  const items = useTOCItems()
  const active = useActiveAnchor()
  const selected = useMemo(
    () => items.findIndex((item) => active === item.url.slice(1)),
    [items, active]
  )
  const path = useTreePath().at(-1)
  const showItem = selected !== -1 && !open

  return (
    <button
      type="button"
      aria-expanded={open}
      onClick={() => setOpen(!open)}
      className={cn(
        'focus-ring px-content-sides text-muted-foreground hover:text-foreground flex h-10 w-full items-center text-start text-xs tracking-wide transition-[color] duration-[var(--duration-fast)] ease-[var(--ease-out)] [&_svg]:size-4',
        className
      )}
      data-toc-popover-trigger=""
      {...props}
    >
      <div className="mx-auto flex w-full max-w-2xl items-center gap-2.5 2xl:max-w-3xl">
        <ProgressHexagon
          value={(selected + 1) / Math.max(1, items.length)}
          max={1}
          className={cn('shrink-0', open && 'text-foreground')}
        />
        <span className="grid flex-1 *:col-start-1 *:row-start-1 *:my-auto">
          <span
            className={cn(
              'truncate transition-[opacity,translate,color] duration-[var(--duration-fast)] ease-[var(--ease-out)]',
              open && 'text-foreground',
              showItem && 'pointer-events-none -translate-y-full opacity-0'
            )}
          >
            {path?.name ?? text.toc}
          </span>
          <span
            className={cn(
              'truncate transition-[opacity,translate] duration-[var(--duration-fast)] ease-[var(--ease-out)]',
              !showItem && 'pointer-events-none translate-y-full opacity-0'
            )}
          >
            {items[selected]?.title}
          </span>
        </span>
        <CaretDownIcon
          className={cn(
            'mx-0.5 size-4 shrink-0 transition-transform duration-[var(--duration-fast)] ease-[var(--ease-out)]',
            open && 'rotate-180'
          )}
        />
      </div>
    </button>
  )
}

interface ProgressHexagonProps extends Omit<
  React.ComponentProps<'svg'>,
  'strokeWidth'
> {
  value: number
  strokeWidth?: number
  size?: number
  min?: number
  max?: number
}

function clamp(input: number, min: number, max: number): number {
  if (input < min) return min
  if (input > max) return max
  return input
}

function ProgressHexagon({
  value,
  strokeWidth = 2,
  size = 16,
  min = 0,
  max = 100,
  ...restSvgProps
}: ProgressHexagonProps) {
  const normalizedValue = clamp(value, min, max)

  const radius = (size - strokeWidth) / 2
  const centerX = size / 2
  const centerY = size / 2

  const points: [number, number][] = []
  for (let i = 0; i < 6; i++) {
    const angle = (90 - i * 60) * (Math.PI / 180)
    const x = centerX + radius * Math.cos(angle)
    const y = centerY - radius * Math.sin(angle)
    points.push([x, y])
  }

  const perimeter = 7 * radius
  const progress = (normalizedValue / max) * perimeter

  const extendedPoints = [...points, points[0], points[1]]
  const pathD = extendedPoints
    .map((p, i) => `${i === 0 ? 'M' : 'L'}${p[0]},${p[1]}`)
    .join(' ')

  return (
    <svg
      role="progressbar"
      viewBox={`0 0 ${size} ${size}`}
      aria-valuenow={normalizedValue}
      aria-valuemin={min}
      aria-valuemax={max}
      {...restSvgProps}
    >
      <path
        d={pathD}
        fill="none"
        strokeWidth={strokeWidth}
        strokeLinejoin="round"
        className="stroke-current/25"
      />
      <path
        d={pathD}
        fill="none"
        stroke="currentColor"
        strokeWidth={strokeWidth}
        strokeLinejoin="round"
        strokeDasharray={perimeter}
        strokeDashoffset={perimeter - progress}
        className="transition-[stroke-dashoffset]"
        style={{ transformOrigin: 'center' }}
      />
    </svg>
  )
}

export function PageTOCPopoverContent(props: ComponentProps<'div'>) {
  const { open } = use(TocPopoverContext)!
  if (!open) return null
  return (
    <div
      data-toc-popover-content=""
      {...props}
      className={cn('mount-enter flex max-h-[50vh] flex-col', props.className)}
    >
      <div className="px-content-sides mx-auto w-full max-w-2xl 2xl:max-w-3xl">
        {props.children}
      </div>
    </div>
  )
}
