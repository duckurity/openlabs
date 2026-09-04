/**
 * Challenge creator card for the right sidebar. Links the author's
 * GitHub profile with avatar when the sync resolved a username,
 * otherwise the lab's commit history.
 */

interface LabCreatorProps {
  name?: string
  url?: string
  avatar?: string
  date?: string
}

export function LabCreator({ name, url, avatar, date }: LabCreatorProps) {
  if (!name || !url) return null

  return (
    <div className="bg-muted flex flex-col gap-2 px-6 py-4 font-mono">
      <span className="text-xs font-medium text-muted-foreground">
        Created by
      </span>
      <a
        href={url}
        target="_blank"
        rel="noopener noreferrer"
        className="focus-ring inline-flex items-center gap-2 outline-none"
      >
        {avatar && (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={avatar}
            alt=""
            width={20}
            height={20}
            loading="lazy"
            className="size-5 shrink-0"
          />
        )}
        <span className="truncate text-xs text-foreground hover:text-primary">
          {name}
        </span>
      </a>
      {date && (
        <span className="tnum text-xs text-muted-foreground">{date}</span>
      )}
    </div>
  )
}
