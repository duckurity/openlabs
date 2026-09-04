import { notFound } from 'next/navigation'
import type { Metadata } from 'next'
import { createRelativeLink } from 'fumadocs-ui/mdx'
import { existsSync } from 'node:fs'
import { join } from 'node:path'

import { source, getLabs, getRelatedLabs, isLabPage, toLabCardData } from '@/lib/source'
import { APP_BASE_URL } from '@/lib/constants'
import { getMDXComponents } from '@/mdx-components'
import { TOC } from '@/components/layout/toc'
import { TOCProvider, TOCScrollArea } from '@/components/toc'
import { TOCItems } from '@/components/toc/clerk'
import {
  PageTOCPopover,
  PageTOCPopoverTrigger,
  PageTOCPopoverContent,
} from '@/components/layout/docs/page/client'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import { PageGithubLinkButton } from '@/components/page-github-link-button'
import { PageActions } from '@/components/layout/page-actions'
import { LabList } from '@/components/lab/lab-list'
import { LabGrid, LabCards } from '@/components/lab/lab-grid'
import { LabCreator } from '@/components/lab/lab-creator'
import { StatusIndicator } from '@/components/status-indicator'
import { CopyButton } from '@/components/copy-button'

export const dynamic = 'force-static'

function categoryLabel(slugs: string[]): string {
  if (slugs.length === 0) return 'Library'
  const head = slugs[0]
  if (head === 'labs') return slugs.length > 1 ? 'Lab' : 'Labs'
  if (head === 'tracks') return 'Tracks'
  if (head === 'play') return 'Guide'
  if (head === 'rules') return 'Rules'
  return head
}

function checkerFor(track?: string, slug?: string): string | null {
  if (!track || !slug) return null
  return `python3 scripts/check.py labs/${track}/${slug}`
}

function jsonLd(
  page: { url: string; data: { title: string; description?: string } },
  opts: { isLab: boolean; isLabsIndex: boolean; labs: { url: string; title: string }[] }
): Record<string, unknown> | null {
  const url = `${APP_BASE_URL}${page.url}`
  if (opts.isLab) {
    return {
      '@context': 'https://schema.org',
      '@type': 'LearningResource',
      name: page.data.title,
      description: page.data.description,
      url,
      teaches: page.data.description,
      isAccessibleForFree: true,
    }
  }
  if (opts.isLabsIndex) {
    return {
      '@context': 'https://schema.org',
      '@type': 'ItemList',
      name: page.data.title,
      description: page.data.description,
      url,
      itemListElement: opts.labs.map((lab, i) => ({
        '@type': 'ListItem',
        position: i + 1,
        name: lab.title,
        url: `${APP_BASE_URL}${lab.url}`,
      })),
    }
  }
  return null
}

export default async function Page(props: PageProps<'/[[...slug]]'>) {
  const params = await props.params
  const page = source.getPage(params.slug)
  if (!page) notFound()

  const MDX = page.data.body
  const toc = page.data.toc
  const hasToc = toc.length > 0
  const isLabsIndex =
    page.slugs.length === 1 && page.slugs[0] === 'labs'
  const isLab = isLabPage(page)
  const isHome = page.slugs.length === 0

  const raw = await page.data.getText('raw').catch(() => page.data.description ?? page.data.title)
  const related = isLab ? getRelatedLabs(page, 3) : []

  const track = page.data.track as string | undefined
  const difficulty = page.data.difficulty as string | undefined
  const port = page.data.port as string | undefined
  const slug = page.slugs[page.slugs.length - 1]
  const checker = isLab ? checkerFor(track, slug) : null
  const structured = jsonLd(page, {
    isLab,
    isLabsIndex,
    labs: getLabs().map((lab) => ({ url: lab.url, title: lab.data.title })),
  })
  const verified = (page.data.verified as boolean | undefined) ?? false
  const creator = {
    name: page.data.author_name as string | undefined,
    url: page.data.author_url as string | undefined,
    avatar: page.data.author_avatar as string | undefined,
    date: page.data.author_date as string | undefined,
  }
  const sheetPath =
    isLab && track && existsSync(join(process.cwd(), 'labs', track, slug, `${slug}.pdf`))
      ? `labs/${track}/${slug}/${slug}.pdf`
      : null

  return (
    <TOCProvider toc={toc}>
      {hasToc && (
        <PageTOCPopover>
          <PageTOCPopoverTrigger />
          <PageTOCPopoverContent>
            <TOCScrollArea>
              <TOCItems />
            </TOCScrollArea>
          </PageTOCPopoverContent>
        </PageTOCPopover>
      )}

      <article
        id="nd-page"
        className={cn(
          'px-content-sides mx-auto w-full max-w-3xl pt-6 pb-14 [grid-area:main] md:pt-8 lg:pb-24 xl:pt-14 2xl:max-w-[900px]',
          'xl:layout:[--fd-toc-width:268px]'
        )}
      >
        <div className="mb-6 flex items-start justify-between gap-4">
          <div className="flex flex-wrap items-center gap-2">
            <Badge>{categoryLabel(page.slugs)}</Badge>
            {isLab && (
              <StatusIndicator
                status={verified ? 'verified' : 'needs-fix'}
              />
            )}
          </div>
          <div className="flex items-center gap-2 max-sm:hidden">
            <PageGithubLinkButton className="max-lg:hidden" path={`content/${page.path}`} />
            <PageActions content={raw} />
          </div>
        </div>

        <h1 className="font-display mb-3 min-w-0 text-3xl leading-tight font-semibold text-balance">
          {page.data.title}
        </h1>

        {page.data.description && (
          <p className="text-foreground/70 mb-4 text-lg">
            {page.data.description}
          </p>
        )}

        {isLab && (
          <dl className="border-border mt-6 grid grid-cols-2 gap-px border bg-transparent font-mono text-sm sm:grid-cols-4">
            {track && (
              <div className="bg-card px-3 py-2">
                <dt className="readout">
                  Track
                </dt>
                <dd>{track}</dd>
              </div>
            )}
            {difficulty && (
              <div className="bg-card px-3 py-2">
                <dt className="readout">
                  Difficulty
                </dt>
                <dd>{difficulty}</dd>
              </div>
            )}
            {port && (
              <div className="bg-card px-3 py-2">
                <dt className="readout">
                  Port
                </dt>
                <dd>:{port}</dd>
              </div>
            )}
            {checker && (
              <div className="bg-card px-3 py-2">
                <dt className="readout">
                  Checker
                </dt>
                <dd className="truncate" title={checker}>
                  check.py
                </dd>
              </div>
            )}
          </dl>
        )}

        {checker && (
          <div className="bg-code mt-4 flex items-center gap-2 px-3 py-2 font-mono text-sm">
            <code className="tnum min-w-0 flex-1 truncate">{checker}</code>
            <CopyButton
              value={checker}
              successNote="Checker copied. Paste it in your terminal to verify your solve."
            />
          </div>
        )}

        {sheetPath && (
          <div className="not-prose mt-4">
            <PageGithubLinkButton path={sheetPath} label="Challenge sheet (PDF)" />
          </div>
        )}

        <div className="not-prose my-0 flex flex-wrap gap-x-2 gap-y-1">
          <PageGithubLinkButton className="lg:hidden" path={`content/${page.path}`} />
          <PageActions className="sm:hidden" content={raw} />
        </div>

        <div className="prose mt-10 flex-1">
          <MDX
            components={getMDXComponents({
              a: createRelativeLink(source, page),
            })}
          />
        </div>

        {isLabsIndex && (
          <LabList labs={getLabs().map(toLabCardData)} />
        )}

        {isHome && (
          <LabGrid className="mt-10">
            <LabCards labs={getLabs().map(toLabCardData)} />
          </LabGrid>
        )}

        {related.length > 0 && (
          <div className="mt-16">
            <h2 className="mb-4 font-mono text-sm tracking-wide">
              Related labs
            </h2>
            <LabGrid>
              <LabCards labs={related.map(toLabCardData)} />
            </LabGrid>
          </div>
        )}
        {structured && (
          <script
            type="application/ld+json"
            dangerouslySetInnerHTML={{ __html: JSON.stringify(structured) }}
          />
        )}
      </article>

      {hasToc && (
        <TOC
          footer={
            isLab ? (
              <LabCreator
                name={creator.name}
                url={creator.url}
                avatar={creator.avatar}
                date={creator.date}
              />
            ) : undefined
          }
        />
      )}
    </TOCProvider>
  )
}

export function generateStaticParams() {
  return source.generateParams()
}

export async function generateMetadata(
  props: PageProps<'/[[...slug]]'>
): Promise<Metadata> {
  const params = await props.params
  const page = source.getPage(params.slug)
  if (!page) notFound()

  return {
    title: page.data.title,
    description: page.data.description,
    alternates: {
      canonical: page.url,
    },
    openGraph: {
      title: page.data.title,
      description: page.data.description,
      url: page.url,
      type: 'article',
    },
    twitter: {
      title: page.data.title,
      description: page.data.description,
    },
  }
}
