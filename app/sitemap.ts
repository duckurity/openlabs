import type { MetadataRoute } from 'next'
import { source } from '@/lib/source'
import { APP_BASE_URL } from '@/lib/constants'

export const dynamic = 'force-static'

export default function sitemap(): MetadataRoute.Sitemap {
  return source.getPages().map((page) => {
    const ogImage = page.data.ogImage as string | undefined
    return {
      url: `${APP_BASE_URL}${page.url}`,
      lastModified: page.data.lastModified ?? undefined,
      changeFrequency: page.slugs.length <= 1 ? 'weekly' : 'monthly',
      priority: page.slugs.length === 0 ? 1 : 0.7,
      ...(ogImage ? { images: [`${APP_BASE_URL}${ogImage}`] } : {}),
    }
  })
}
