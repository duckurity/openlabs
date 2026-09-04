import defaultMdxComponents from 'fumadocs-ui/mdx'
import type * as React from 'react'
import { CodeTabs } from '@/components/code-tabs'

type MDXComponents = Record<string, React.ComponentType<any>>
import { cn } from '@/lib/utils'
import { CopyButton } from '@/components/copy-button'
import { codeClasses } from '@/lib/mdx'

export function getMDXComponents(
  components?: MDXComponents
): MDXComponents {
  return {
    ...defaultMdxComponents,
    CodeTabs,
    code: ({
      className,
      ...props
    }: React.ComponentProps<'code'> & { __raw__?: string }) => {
      if (typeof props.children === 'string') {
        return (
          <code
            className={cn(
              'bg-muted relative rounded-none px-[0.3rem] py-[0.2rem] font-mono text-[0.8rem] wrap-break-word outline-none',
              className
            )}
            {...props}
          />
        )
      }
      return <code className="not-prose" {...props} />
    },
    pre: ({
      className,
      __raw__,
      children,
      ...props
    }: React.ComponentProps<'pre'> & {
      __raw__?: string
      children: React.ReactNode
    }) => (
      <div className={cn('group/code relative', className)}>
        {__raw__ && <CopyButton value={__raw__} />}
        <pre className={codeClasses.pre} {...props}>
          {children}
        </pre>
      </div>
    ),
    ...components,
  }
}
