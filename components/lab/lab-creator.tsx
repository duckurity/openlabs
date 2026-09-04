/**
 * Challenge creator card for the right sidebar. Links the author's
 * GitHub profile with avatar when the sync resolved a username,
 * otherwise the lab's commit history. Shows the PR merger as a
 * second verification row when known and different.
 */

interface Person {
  name?: string
  url?: string
  avatar?: string
}

function PersonRow({ label, person }: { label: string; person: Person }) {
  if (!person.name || !person.url) return null
  return (
    <>
      <span className="text-xs font-medium text-muted-foreground">
        {label}
      </span>
      <a
        href={person.url}
        target="_blank"
        rel={person.avatar ? 'noopener noreferrer me' : 'noopener noreferrer'}
        className="focus-ring inline-flex items-center gap-2 outline-none"
      >
        {person.avatar && (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={person.avatar}
            alt=""
            width={20}
            height={20}
            loading="lazy"
            className="size-5 shrink-0"
          />
        )}
        <span className="truncate text-xs text-foreground hover:text-primary">
          {person.name}
        </span>
      </a>
    </>
  )
}

interface LabCreatorProps {
  name?: string
  url?: string
  avatar?: string
  date?: string
  verifierName?: string
  verifierUrl?: string
  verifierAvatar?: string
}

export function LabCreator({
  name,
  url,
  avatar,
  date,
  verifierName,
  verifierUrl,
  verifierAvatar,
}: LabCreatorProps) {
  if (!name || !url) return null

  return (
    <div className="bg-muted flex flex-col gap-2 px-6 py-4 font-mono">
      <PersonRow label="Created by" person={{ name, url, avatar }} />
      <PersonRow
        label="Verified by"
        person={{ name: verifierName, url: verifierUrl, avatar: verifierAvatar }}
      />
      {date && (
        <span className="tnum text-xs text-muted-foreground">{date}</span>
      )}
    </div>
  )
}
