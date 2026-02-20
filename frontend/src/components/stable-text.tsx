import type { ReactNode } from "react"

/**
 * Reserves the width of the longest candidate string using CSS Grid overlay.
 * All candidates are rendered invisibly in the same grid cell so the browser
 * computes the width from the widest one — no JS measurement needed.
 */
export function StableText({
  candidates,
  children,
}: {
  candidates: string[]
  children: ReactNode
}) {
  return (
    <span className="inline-grid items-center justify-items-center">
      {candidates.map((text) => (
        <span key={text} className="invisible col-start-1 row-start-1">
          {text}
        </span>
      ))}
      <span className="col-start-1 row-start-1">{children}</span>
    </span>
  )
}
