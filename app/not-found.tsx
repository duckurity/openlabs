import Link from 'next/link'
import { Button } from '@/components/ui/button'

export default function NotFound() {
  return (
    <div className="mx-auto flex w-full max-w-3xl flex-col items-start gap-4 px-6 py-24">
      <p className="font-mono text-sm tracking-wide">404</p>
      <h1 className="font-display text-3xl leading-tight font-semibold">Page not found</h1>
      <p className="text-foreground/70 text-lg">
        The page you asked for does not exist. Pick a lab and keep solving.
      </p>
      <Button asChild>
        <Link href="/">Back home</Link>
      </Button>
    </div>
  )
}
