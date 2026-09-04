import { notFound } from 'next/navigation'
import type { Metadata } from 'next'
import { createRelativeLink } from 'fumadocs-ui/mdx'
import { existsSync } from 'node:fs'
import { join } from 'node:path'

import { source, getLabs, getRelatedLabs, isLabPage, toLabCardData } from '@/lib/source'
import { APP_BASE_URL } from '@/lib/constants'
import {
  breadcrumbJsonLd,
  faqJsonLd,
  faqPairs,
  guideJsonLd,
  labJsonLd,
  labsIndexJsonLd,
} from '@/lib/schema'
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
  const labs = getLabs().map((lab) => ({ url: lab.url, title: lab.data.title }))

  const track = page.data.track as string | undefined
  const difficulty = page.data.difficulty as string | undefined
  const port = page.data.port as string | undefined
  const slug = page.slugs[page.slugs.length - 1]
  const checker = isLab ? checkerFor(track, slug) : null
  const verified = (page.data.verified as boolean | undefined) ?? false
  const score = page.data.score as number | undefined
  const scoreGrade = page.data.score_grade as string | undefined
  const scoreTone =
    score === undefined
      ? ''
      : score >= 80
        ? 'text-(--status-success-strong)'
        : score >= 70
          ? 'text-(--status-warning-strong)'
          : 'text-(--status-error-strong)'
  const creator = {
    name: page.data.author_name as string | undefined,
    url: page.data.author_url as string | undefined,
    avatar: page.data.author_avatar as string | undefined,
    date: page.data.author_date as string | undefined,
    verifierName: page.data.verifier_name as string | undefined,
    verifierUrl: page.data.verifier_url as string | undefined,
    verifierAvatar: page.data.verifier_avatar as string | undefined,
  }
  const sheetPath =
    isLab && track && existsSync(join(process.cwd(), 'labs', track, slug, `${slug}.pdf`))
      ? `labs/${track}/${slug}/${slug}.pdf`
      : null
  const keywords = page.data.keywords as
    | { primary?: string; secondary?: string[] }
    | undefined
  const image = (page.data.ogImage as string | undefined) ?? '/opengraph-image.png'
  const lastModified =
    page.data.lastModified instanceof Date
      ? page.data.lastModified.toISOString()
      : (page.data.lastModified as string | undefined)
  const structured: Record<string, unknown>[] = [
    ...(breadcrumbJsonLd(page.slugs) ? [breadcrumbJsonLd(page.slugs) as Record<string, unknown>] : []),
    ...(isLab
      ? [
          labJsonLd({
            url: page.url,
            title: page.data.title,
            description: page.data.description,
            image,
            dateModified: lastModified,
            keywords,
            section: track,
            authorName: creator.name,
            authorUrl: creator.url,
            datePublished: creator.date,
            difficulty: difficulty,
            intent: page.data.intent as string | undefined,
          }),
        ]
      : isLabsIndex
        ? [
            labsIndexJsonLd(page.url, page.data.title, page.data.description, labs),
          ]
        : [
            guideJsonLd({
              url: page.url,
              title: page.data.title,
              description: page.data.description,
              image,
              dateModified: lastModified,
              keywords,
              section: page.data.type as string | undefined,
              technical:
                page.slugs[0] === 'play' || page.slugs[0] === 'technique',
            }),
          ]),
    ...(page.slugs.length === 1 && page.slugs[0] === 'faq'
      ? [faqJsonLd(page.url, faqPairs(raw))].filter(
          (block): block is Record<string, unknown> => block !== null
        )
      : []),
  ]

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
          <dl className="border-border mt-6 grid grid-cols-2 gap-px border bg-transparent font-mono text-sm sm:grid-cols-5">
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
            {score !== undefined && (
              <div className="bg-card px-3 py-2">
                <dt className="readout">
                  Score
                </dt>
                <dd className={`tnum ${scoreTone}`}>
                  {score}{scoreGrade ? ` ${scoreGrade}` : ''}
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
        {structured.map((block, i) => (
          <script
            key={i}
            type="application/ld+json"
            dangerouslySetInnerHTML={{ __html: JSON.stringify(block) }}
          />
        ))}
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
                verifierName={creator.verifierName}
                verifierUrl={creator.verifierUrl}
                verifierAvatar={creator.verifierAvatar}
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

  const image = (page.data.ogImage as string | undefined) ?? '/opengraph-image.png'
  const keywords = [
    ...((page.data.keywords as { primary?: string; secondary?: string[] } | undefined)?.primary
      ? [(page.data.keywords as { primary?: string }).primary as string]
      : []),
    ...((page.data.keywords as { secondary?: string[] } | undefined)?.secondary ?? []),
  ]
  const authorName = page.data.author_name as string | undefined
  const authorUrl = page.data.author_url as string | undefined

  return {
    title: page.data.title,
    description: page.data.description,
    keywords: keywords.length > 0 ? keywords : undefined,
    authors: authorName ? [{ name: authorName, url: authorUrl }] : undefined,
    alternates: {
      canonical: page.url,
    },
    openGraph: {
      title: page.data.title,
      description: page.data.description,
      url: page.url,
      type: 'article',
      locale: 'en_US',
      images: [
        {
          url: image,
          width: 1200,
          height: 630,
          alt: page.data.title,
        },
      ],
      publishedTime: (page.data.author_date as string | undefined) ?? page.data.lastModified?.toString(),
      modifiedTime: page.data.lastModified?.toString(),
      authors: authorName ? [authorName] : undefined,
    },
    twitter: {
      card: 'summary_large_image',
      title: page.data.title,
      description: page.data.description,
      images: [image],
    },
  }
}
