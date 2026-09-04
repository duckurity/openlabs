/**
 * GitHub API client for repository metadata.
 *
 * Uses the public REST API — no key required. Optionally reads
 * `GITHUB_TOKEN` to raise the rate limit. Returns null on failure
 * so callers can render without a count.
 */

export interface GitHubRepo {
  fullName: string
  stars: number
}

export async function fetchGitHubRepo(
  owner: string,
  repo: string
): Promise<GitHubRepo | null> {
  try {
    const response = await fetch(
      `https://api.github.com/repos/${owner}/${repo}`,
      {
        headers: {
          Accept: 'application/vnd.github.v3+json',
          'User-Agent': 'openlabs-site',
          ...(process.env.GITHUB_TOKEN
            ? { Authorization: `Bearer ${process.env.GITHUB_TOKEN}` }
            : {}),
        },
      }
    )
    if (!response.ok) return null
    const data = await response.json()
    if (
      typeof data.full_name !== 'string' ||
      typeof data.stargazers_count !== 'number'
    ) {
      return null
    }
    return { fullName: data.full_name, stars: data.stargazers_count }
  } catch {
    return null
  }
}

export function formatCount(count: number): string {
  if (count >= 1_000_000) {
    const value = count / 1_000_000
    return `${value % 1 === 0 ? value.toFixed(0) : value.toFixed(1)}m`
  }
  if (count >= 1_000) {
    const value = count / 1_000
    return `${value % 1 === 0 ? value.toFixed(0) : value.toFixed(1)}k`
  }
  return count.toLocaleString('en-US')
}
