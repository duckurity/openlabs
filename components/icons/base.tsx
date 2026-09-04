import * as React from 'react'
import type { Icon as PhosphorIcon } from '@phosphor-icons/react/dist/lib/types'

/* Brand lock: every icon ships Phosphor Bold in currentColor.
   Callers size via className only. Weight is not overridable. */
export function createIcon(Icon: PhosphorIcon) {
  function BrandIcon(props: React.SVGProps<SVGSVGElement>) {
    return <Icon weight="bold" color="currentColor" {...props} />
  }
  return BrandIcon
}
