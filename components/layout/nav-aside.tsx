'use client'

import { sitemap } from '@/lib/sitemap'
import Link from 'next/link'
import React, { SVGProps } from 'react'
import { Logo } from '../logos'
import { cn } from '@/lib/utils'
import { usePathname } from 'next/navigation'
import { Button } from '../ui/button'
import { ThemeToggle } from './theme-toggle'

export const NavAside = () => {
  const pathname = usePathname()

  return (
    <div className="w-aside-width flex h-screen shrink-0 flex-col gap-1 self-start max-md:hidden">
      <Link
        href="/"
        aria-label="openlabs home"
        className="focus-ring group relative flex size-aside-width items-center justify-center bg-primary text-(--neutral-950) transition-transform duration-[var(--duration-instant)] ease-[var(--ease-out)] outline-none active:scale-[0.96]"
      >
        <span
          aria-hidden="true"
          className="absolute inset-x-3 top-1.5 h-px bg-(--neutral-950)/25 opacity-0 transition-opacity duration-[var(--duration-fast)] ease-[var(--ease-out)] group-hover:opacity-100"
        />
        <Logo className="size-12" mark="var(--neutral-0)" />
      </Link>
      {sitemap.map((item) => {
        const isActive = pathname.startsWith(item.href)
        return (
          <AsideButton
            key={item.href}
            icon={item.icon}
            label={item.label}
            tooltip={isActive ? undefined : item.label}
            active={isActive}
            asChild
          >
            <Link href={item.href} />
          </AsideButton>
        )
      })}
      <div className="bg-muted flex-1" />
      <ThemeToggle />
    </div>
  )
}

type AsideButtonProps = Omit<
  React.ComponentProps<typeof Button>,
  'variant' | 'size'
> & {
  icon?: React.ComponentType<SVGProps<SVGSVGElement>>
  label?: string
  active?: boolean
  tooltip?: string
}

export const AsideButton = ({
  icon: Icon,
  label,
  active = false,
  tooltip,
  className,
  children,
  asChild,
  ...props
}: AsideButtonProps) => {
  const content =
    Icon && label ? (
      <>
        <Icon className={cn('size-5 transition-transform duration-[var(--duration-normal)] ease-[var(--ease-out)]', active && 'rotate-90')} />
        <span className={cn('text-sm 2xl:text-base', !active && 'sr-only')}>
          {label}
        </span>
      </>
    ) : (
      children
    )

  const buttonClassName = cn(
    'bg-muted text-muted-foreground w-aside-width flex items-center justify-center gap-2 font-mono font-medium tracking-wide transition-colors',
    active
      ? 'bg-accent hover:bg-accent text-accent-foreground h-auto rotate-180 px-6 [writing-mode:vertical-rl]'
      : 'h-aside-width size-aside-width hover:bg-accent/50 hover:text-foreground',
    className
  )

  if (asChild && React.isValidElement(children)) {
    const child = children as React.ReactElement<{
      children?: React.ReactNode
      className?: string
      title?: string
    }>
    return React.cloneElement(child, {
      ...props,
      title: tooltip ?? child.props.title,
      className: cn(buttonClassName, child.props.className),
      children: Icon && label ? content : child.props.children,
    })
  }

  return (
    <Button
      variant="muted"
      size="icon"
      title={tooltip}
      className={buttonClassName}
      {...props}
    >
      {content}
    </Button>
  )
}
