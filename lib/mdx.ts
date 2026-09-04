import type { ShikiTransformer } from 'shiki'

/*
 * Shiki transformers (MDX level). Tag every code block with its raw source
 * so the rendered <pre> can offer a copy button.
 */
export const transformers = [
  {
    pre(node) {
      node.properties['__raw__'] = this.source
    },
    code(node) {
      if (node.tagName === 'code') {
        node.properties['__raw__'] = this.source
      }
    },
  },
] satisfies ShikiTransformer[]

export const codeClasses = {
  pre: "not-fumadocs-codeblock relative w-full overflow-auto p-4 has-[[data-line-numbers]]:px-0",
}
