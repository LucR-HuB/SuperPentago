import { useEffect, useMemo, useState } from "react"
import Board, { type BoardPhase, type Coord } from "./components/Board"
import { apiNew, apiPlay, apiBot } from "./api"
import type { GameState } from "./types"

type Q = "Q00" | "Q01" | "Q10" | "Q11"
type D = "CW" | "CCW"

type EngineId = "minimax" | "mcts" | "policy"

const ENGINES: { id: EngineId; title: string; desc: string; traits: string[]; ready: boolean }[] = [
  { id: "minimax", title: "Minimax αβ", desc: "Recherche déterministe avec élagage alpha-beta. Forte tactique courte portée.", traits: ["Déterministe", "Rapide", "Forces tactiques"], ready: true },
  { id: "mcts", title: "MCTS", desc: "Arbre de Monte-Carlo guidé par simulations. Bon milieu de partie.", traits: ["Stochastique", "Évolutif"], ready: false },
  { id: "policy", title: "Policy + Value", desc: "Réseau de politique/valeur type AlphaZero. Apprentissage auto-jeu.", traits: ["Appris", "Évaluation rapide"], ready: false },
]

function parseMove(m: string): { r: number; c: number; q: Q; d: D } {
  const [cell, q, d] = m.trim().split(/\s+/)
  const c = "ABCDEF".indexOf(cell[0])
  const r = "123456".indexOf(cell[1])
  return { r, c, q: q as Q, d: d as D }
}

function segments(): Array<Array<{r:number;c:number}>> {
  const out: Array<Array<{r:number;c:number}>> = []
  for (let r=0;r<6;r++) for (let c=0;c<=1;c++) out.push([...Array(5)].map((_,k)=>({r,c:c+k})))
  for (let c=0;c<6;c++) for (let r=0;r<=1;r++) out.push([...Array(5)].map((_,k)=>({r:r+k,c})))
  for (let r=0;r<6;r++) for (let c=0;c<6;c++){
    if (r+4<6 && c+4<6) out.push([...Array(5)].map((_,k)=>({r:r+k,c:c+k})))
    if (r+4<6 && c-4>=0) out.push([...Array(5)].map((_,k)=>({r:r+k,c:c-k})))
  }
  const uniq: typeof out = []
  const seen = new Set<string>()
  for (const s of out){ const key = s.map(p=>`${p.r},${p.c}`).join(";"); if (!seen.has(key)){ seen.add(key); uniq.push(s) } }
  return uniq
}
const SEGS = segments()

function winningCells(grid: number[][]): {r:number;c:number}[] | null {
  for (const s of SEGS){
    const v = grid[s[0].r][s[0].c]; if (v===0) continue
    let ok = true
    for (let k=1;k<5;k++){ if (grid[s[k].r][s[k].c] !== v){ ok=false; break } }
    if (ok) return s
  }
  return null
}

export default function App() {
  const [gid, setGid] = useState<string>("")
  const [state, setState] = useState<GameState | null>(null)
  const [phase, setPhase] = useState<BoardPhase>("place")
  const [selectedCell, setSelectedCell] = useState<Coord | null>(null)
  const [selectedQuadrant, setSelectedQuadrant] = useState<Q | null>(null)
  const [anim, setAnim] = useState<{q: Q; dir: D; stage: "rotating" | "reset"} | null>(null)
  const [depth, setDepth] = useState<number>(3)
  const [timeMs, setTimeMs] = useState<number | undefined>(undefined)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState("")
  const [human, setHuman] = useState<"B" | "W">("B")
  const [showColorModal, setShowColorModal] = useState(false)
  const [engine, setEngine] = useState<EngineId>("minimax")
  const [showEngineModal, setShowEngineModal] = useState(false)

  const bot = human === "B" ? "W" : "B"

  useEffect(() => {
    apiNew().then(res => { setGid(res.game_id); setState(res.state); setError("") }).catch(()=>setError("init"))
  }, [])

  const win = useMemo(() => state ? winningCells(state.grid) : null, [state])
  const bgClass = state ? (state.to_move === human ? "bg-human" : "bg-bot") : "bg-neutral"
  const canHoverTiles = !!state && !state.terminal && state.to_move === human && phase === "place"

  function onCellClick(r: number, c: number) {
    if (busy || !state || state.terminal) return
    if (state.to_move !== human) return
    if (phase !== "place") return
    if (state.grid[r][c] !== 0) return
    setSelectedCell({ r, c })
    setSelectedQuadrant(null)
    setPhase("rotate")
  }

  function onQuadrantClick(q: Q) {
    if (busy || !state || state.terminal) return
    if (phase !== "rotate") return
    setSelectedQuadrant(q)
  }

  async function onRotate(dir: D) {
    if (busy || !state || state.terminal) return
    if (phase !== "rotate" || !selectedCell || !selectedQuadrant) return
    setBusy(true)
    setAnim({ q: selectedQuadrant, dir, stage: "rotating" })
    try {
      const cell = "ABCDEF"[selectedCell.c] + "123456"[selectedCell.r]
      const res = await apiPlay(gid, cell, selectedQuadrant, dir)
      setTimeout(() => {
        setState(res.state)
        setSelectedCell(null)
        setSelectedQuadrant(null)
        setAnim(a => a ? { ...a, stage: "reset" } : null)
        requestAnimationFrame(() => setAnim(null))
        setPhase("place")
        setBusy(false)
      }, 320)
    } catch {
      setAnim(null)
      setBusy(false)
      setError("play")
    }
  }

  async function triggerBot() {
    if (busy || !state || state.terminal) return
    if (state.to_move !== bot) return
    setBusy(true)
    setError("")
    try {
      const res = await apiBot(gid, depth, timeMs, engine)
      const { r, c, q, d } = parseMove(res.move)
      setSelectedCell({ r, c })
      setSelectedQuadrant(q)
      setPhase("rotate")
      setTimeout(() => {
        setAnim({ q, dir: d, stage: "rotating" })
        setTimeout(() => {
          setState(res.state)
          setSelectedCell(null)
          setSelectedQuadrant(null)
          setAnim(a => a ? { ...a, stage: "reset" } : null)
          requestAnimationFrame(() => setAnim(null))
          setPhase("place")
          setBusy(false)
        }, 320)
      }, 0)
    } catch {
      setBusy(false)
      setError("bot")
    }
  }

  useEffect(() => {
    if (!state || state.terminal) return
    if (state.to_move === bot && !busy) triggerBot()
  }, [state, busy, bot, engine, depth, timeMs])

  async function startNewGame(h: "B" | "W") {
    if (busy) return
    setShowColorModal(false)
    setHuman(h)
    setBusy(true)
    try {
      const res = await apiNew()
      setGid(res.game_id)
      setState(res.state)
      setSelectedCell(null)
      setSelectedQuadrant(null)
      setPhase("place")
      setAnim(null)
      setError("")
      setTimeout(() => {
        if (res.state.to_move !== h) triggerBot()
      }, 0)
    } finally {
      setBusy(false)
    }
  }

  function openNewGameModal() {
    if (busy) return
    setShowColorModal(true)
  }

  function winnerText() {
    if (!state || !state.terminal) return ""
    if (!state.winner) return "Match nul"
    const who = state.winner === human ? "Tu gagnes" : "L’IA gagne"
    return who
  }

  return (
    <div className={"min-h-screen w-full " + bgClass}>
      <div className="mx-auto max-w-6xl px-6 py-10">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-3xl font-extrabold tracking-tight drop-shadow-sm">SuperPentago</h1>
          <div className="flex items-center gap-3">
            <button className="px-3 py-2 rounded-lg bg-white border border-gray-300 shadow-sm text-sm"
                    onClick={()=>setShowEngineModal(true)}>
              IA : {ENGINES.find(e=>e.id===engine)?.title || "—"}
            </button>
            <div className="flex items-center gap-2">
              <label className="text-sm">Profondeur: {depth}</label>
              <input type="range" min={1} max={6} value={depth} onChange={(e)=>setDepth(parseInt(e.target.value))}/>
            </div>
            <button onClick={openNewGameModal} disabled={busy} className="px-4 py-2 rounded-lg bg-white border border-gray-300 shadow-sm">New game</button>
          </div>
        </div>

        {state && (
          <div className="relative grid grid-cols-1 md:grid-cols-[auto_320px] gap-8">
            {busy && state.to_move !== human && (
              <div className="thinking">
                <div className="loader"></div>
                <div className="mt-2 text-sm">IA réfléchit…</div>
              </div>
            )}

            {state.terminal && (
              <div className="modal-backdrop">
                <div className="modal">
                  <div className="modal-title">{winnerText()}</div>
                  <div className="modal-actions">
                    <button className="btn-choice" onClick={openNewGameModal}>Nouvelle partie</button>
                  </div>
                </div>
              </div>
            )}

            <div className="flex flex-col items-center gap-4">
              <Board
                grid={state.grid}
                toMove={state.to_move}
                phase={phase}
                selectedCell={selectedCell}
                selectedQuadrant={selectedQuadrant}
                anim={anim}
                winning={state.terminal ? win : null}
                canHoverTiles={canHoverTiles}
                onCellClick={onCellClick}
                onQuadrantClick={onQuadrantClick}
                onRotate={onRotate}
              />
              <div className="text-sm">
                {state.terminal ? (state.winner ? `Gagnant : ${state.winner}` : "Match nul") : `Au tour de : ${state.to_move}`}
              </div>
              {error && <div className="text-sm text-red-700 bg-red-100 px-3 py-1 rounded">{error}</div>}
            </div>

            <div className="bg-white rounded-2xl border border-gray-200 shadow p-4 flex flex-col gap-3">
              <div className="text-sm font-semibold">Paramètres IA</div>
              <div className="text-sm">Moteur : {ENGINES.find(e=>e.id===engine)?.title}</div>
              <div className="text-sm">Temps (ms)</div>
              <input type="number" min={0} placeholder="ms" value={timeMs ?? ""} onChange={e=>setTimeMs(e.target.value===""? undefined : parseInt(e.target.value))} className="border border-gray-300 rounded px-2 py-1"/>
              <div className="text-xs break-all text-gray-500">Game ID: {gid}</div>
            </div>
          </div>
        )}

        {showColorModal && (
          <div className="modal-backdrop">
            <div className="modal">
              <div className="modal-title">Choisis ta couleur</div>
              <div className="modal-actions">
                <button className="btn-choice btn-black" onClick={()=>startNewGame("B")}>Noir</button>
                <button className="btn-choice btn-white" onClick={()=>startNewGame("W")}>Blanc</button>
              </div>
              <div className="modal-footer">
                <button className="btn-cancel" onClick={()=>setShowColorModal(false)}>Annuler</button>
              </div>
            </div>
          </div>
        )}

        {showEngineModal && (
          <div className="modal-backdrop" onClick={()=>setShowEngineModal(false)}>
            <div className="modal" onClick={(e)=>e.stopPropagation()}>
              <div className="flex items-center gap-2">
                <div className="modal-title">Choisir l’IA</div>
                <div className="ai-badge">Catalogue</div>
              </div>
              <div className="ai-grid">
                {ENGINES.map(e=>(
                  <div key={e.id} className={"ai-card " + (!e.ready ? "disabled" : "")}>
                    <div className="flex items-center justify-between">
                      <div className="ai-title">{e.title}</div>
                      {!e.ready && <div className="ai-badge">Bientôt</div>}
                    </div>
                    <div className="ai-desc">{e.desc}</div>
                    <div className="ai-traits">
                      {e.traits.map(t=> <div key={t} className="ai-chip">{t}</div>)}
                    </div>
                    {e.ready && (
                      <button className="choose" onClick={()=>{ setEngine(e.id); setShowEngineModal(false) }}>
                        Sélectionner
                      </button>
                    )}
                  </div>
                ))}
              </div>
              <div className="modal-footer">
                <button className="btn-cancel" onClick={()=>setShowEngineModal(false)}>Fermer</button>
              </div>
            </div>
          </div>
        )}

      </div>
    </div>
  )
}