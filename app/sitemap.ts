import type { MetadataRoute } from 'next'
import { source } from '@/lib/source'
import { APP_BASE_URL } from '@/lib/constants'

export const dynamic = 'force-static'

export default function sitemap(): MetadataRoute.Sitemap {
  return source.getPages().map((page) => ({
    url: `${APP_BASE_URL}${page.url}`,
    priority: page.slugs.length === 0 ? 1 : 0.7,
  }))
}
