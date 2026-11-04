// Keep this literal aligned with contracts/tracks.json.
// scripts/test_track_registry.py enforces parity.
export const TRACKS = [
  'web',
  'binary',
  'crypto',
  'network',
  'osint',
  'forensics',
  'misc',
] as const

export type Track = (typeof TRACKS)[number]
