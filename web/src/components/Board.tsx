import React, { useMemo } from "react"

type Q = "Q00" | "Q01" | "Q10" | "Q11"
type D = "CW" | "CCW"
type AnimStage = "rotating" | "reset"

export type BoardPhase = "place" | "rotate"
export type Coord = { r: number; c: number }
export type Grid = number[][]

type Props = {
  grid: Grid
  toMove: "B" | "W"
  phase: BoardPhase
  selectedCell: Coord | null
  selectedQuadrant: Q | null
  anim: { q: Q; dir: D; stage: AnimStage } | null
  winning: Coord[] | null
  canHoverTiles: boolean
  onCellClick: (r: number, c: number) => void
  onQuadrantClick: (q: Q) => void
  onRotate: (dir: D) => void
}

const QLIST: Q[] = ["Q00", "Q01", "Q10", "Q11"]

function Disc({ v, ghost }: { v: 0 | 1 | 2; ghost?: boolean }) {
  const cls = ghost ? "opacity-60" : ""
  if (v === 1) return <div className={`w-8 h-8 rounded-full shadow-sm ${cls}`} style={{ background: "radial-gradient(circle at 30% 30%, #444 0%, #111 60%, #000 100%)" }}/>
  if (v === 2) return <div className={`w-8 h-8 rounded-full border border-gray-500 shadow-sm ${cls}`} style={{ background: "radial-gradient(circle at 30% 30%, #fff 0%, #f3f3f3 60%, #e6e6e6 100%)" }}/>
  return <div className="w-8 h-8"/>
}

export default function Board({
  grid,
  toMove,
  phase,
  selectedCell,
  selectedQuadrant,
  anim,
  winning,
  canHoverTiles,
  onCellClick,
  onQuadrantClick,
  onRotate,
}: Props) {
  const winKey = useMemo(() => new Set((winning ?? []).map(p => `${p.r},${p.c}`)), [winning])
  const gh = selectedCell ? (toMove === "B" ? 1 : 2) : 0

  function plateRotStyle(q: Q): React.CSSProperties {
    if (!anim || anim.q !== q) return { transition: "transform 320ms ease-out" }
    if (anim.stage === "rotating") return { transition: "transform 320ms ease-out", transform: `rotate(${anim.dir === "CW" ? 90 : -90}deg)` }
    return { transition: "none", transform: "none" }
  }

  return (
    <div className="scene">
      <div className="board3d">
        {QLIST.map((q) => {
          const r0 = q === "Q00" || q === "Q01" ? 0 : 3
          const c0 = q === "Q00" || q === "Q10" ? 0 : 3
          const sel = selectedQuadrant === q
          const clickable = phase === "rotate"
          return (
            <div
              key={q}
              className={`plate plate-float ${clickable ? "plate--clickable plate--hoverable" : ""} ${sel ? "plate--selected" : ""}`}
              onClick={clickable ? (() => onQuadrantClick(q)) : undefined}
            >
              <div className="plate-rot" style={plateRotStyle(q)}>
                <div className="grid grid-cols-3 gap-2">
                  {[0,1,2].flatMap(i =>
                    [0,1,2].map(j => {
                      const r = r0 + i, c = c0 + j
                      const v = grid[r][c] as 0|1|2
                      const ghost = selectedCell && selectedCell.r === r && selectedCell.c === c
                      const win = winKey.has(`${r},${c}`)
                      return (
                        <div
                          key={`${r}-${c}`}
                          className={`tile ${win ? "ring-4 ring-emerald-500" : ""} ${canHoverTiles ? "tile--active" : ""}`}
                          onPointerDown={(e)=>{ e.stopPropagation(); onCellClick(r,c) }}
                        >
                          <Disc v={v}/>
                          {ghost && <div className="ghost"><Disc v={gh as 1|2} ghost/></div>}
                        </div>
                      )
                    })
                  )}
                </div>
              </div>

              {phase === "rotate" && sel && (
                <div className="overlay-rotate">
                  <button className="arrow-btn" onClick={(e)=>{e.stopPropagation(); onRotate("CCW")}}>↶</button>
                  <button className="arrow-btn" onClick={(e)=>{e.stopPropagation(); onRotate("CW")}}>↷</button>
                </div>
              )}
            </div>
          )
        })}
      </div>
      <div className="mt-3 text-center text-xs text-amber-800">
        {phase === "place" ? "Clique une case pour poser ta bille" : "Clique un cadran puis choisis la flèche pour le faire pivoter"}
      </div>
    </div>
  )
}