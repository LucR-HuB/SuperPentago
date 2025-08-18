import { useEffect, useMemo, useState, useRef } from "react"
import Board, { type BoardPhase, type Coord } from "./components/Board"
import { apiNew, apiPlay, apiBot, apiProgress } from "./api"
import type { GameState } from "./types"

type Q = "Q00" | "Q01" | "Q10" | "Q11"
type D = "CW" | "CCW"
type EngineId = "minimax" | "mcts" | "policy"
type Mode = "hvb" | "bvb"
type BotPost = {
  depth: number
  timeMs?: number
  engine: EngineId
  simulations?: number
}
type BotCfg = {
  engine: EngineId
  // Minimax params
  mmDepth: number
  mmTimeMs?: number
  // MCTS params
  mcSims: number
  mcTimeMs?: number
}

const ENGINES: { id: EngineId; title: string; desc: string; ready: boolean }[] = [
  { id: "minimax", title: "Minimax αβ", desc: "Recherche déterministe avec élagage alpha-beta.", ready: true },
  { id: "mcts", title: "MCTS", desc: "Arbre Monte-Carlo guidé par simulations.", ready: true },
  { id: "policy", title: "Policy + Value", desc: "Réseau type AlphaZero.", ready: false },
]

function parseMove(m: string): { r: number; c: number; q: Q; d: D } {
  const [cell, q, d] = m.trim().split(/\s+/)
  const c = "ABCDEF".indexOf(cell[0])
  const r = "123456".indexOf(cell[1])
  return { r, c, q: q as Q, d: d as D }
}

function segments(): Array<Array<{ r: number; c: number }>> {
  const out: Array<Array<{ r: number; c: number }>> = []
  for (let r = 0; r < 6; r++) for (let c = 0; c <= 1; c++) out.push([...Array(5)].map((_, k) => ({ r, c: c + k })))
  for (let c = 0; c < 6; c++) for (let r = 0; r <= 1; r++) out.push([...Array(5)].map((_, k) => ({ r: r + k, c })))
  for (let r = 0; r < 6; r++) for (let c = 0; c < 6; c++) {
    if (r + 4 < 6 && c + 4 < 6) out.push([...Array(5)].map((_, k) => ({ r: r + k, c: c + k })))
    if (r + 4 < 6 && c - 4 >= 0) out.push([...Array(5)].map((_, k) => ({ r: r + k, c: c - k })))
  }
  const uniq: typeof out = []
  const seen = new Set<string>()
  for (const s of out) {
    const key = s.map(p => `${p.r},${p.c}`).join(";")
    if (!seen.has(key)) { seen.add(key); uniq.push(s) }
  }
  return uniq
}
const SEGS = segments()

function winningCells(grid: number[][]): { r: number; c: number }[] | null {
  for (const s of SEGS) {
    const v = grid[s[0].r][s[0].c]; if (v === 0) continue
    let ok = true
    for (let k = 1; k < 5; k++) { if (grid[s[k].r][s[k].c] !== v) { ok = false; break } }
    if (ok) return s
  }
  return null
}

/* ====================== Barre de progression — polling serveur ====================== */
type ServerProgress = {
  engine: "mcts" | "minimax" | string
  sims_done?: number
  sims_target?: number
  elapsed_ms?: number
  time_ms?: number
}

function formatMs(ms?: number) {
  if (ms === undefined) return ""
  if (ms < 1000) return `${Math.round(ms)} ms`
  return `${(ms / 1000).toFixed(1)} s`
}

// remplace TOUT ton hook useProgressPolling par ceci :
function useProgressPolling() {
  const [visible, setVisible] = useState(false)
  const [label, setLabel] = useState("")
  const [percent, setPercent] = useState(0)
  const [indeterminate, setIndeterminate] = useState(true)
  const [extra, setExtra] = useState<string>("")
  const intervalRef = useRef<number | null>(null)
  const lastGidRef = useRef<string | null>(null)

  function clearTimer() {
    if (intervalRef.current !== null) {
      clearInterval(intervalRef.current)
      intervalRef.current = null
    }
  }

  function stop() {
    clearTimer()
    setPercent(1)
    setTimeout(() => {
      setVisible(false)
      setPercent(0)
      setExtra("")
      setLabel("")
      setIndeterminate(true)
    }, 200)
  }

  function start(gid: string, text: string) {
    // TOUJOURS redémarrer proprement
    if (intervalRef.current !== null) {
      clearInterval(intervalRef.current)
      intervalRef.current = null
    }
  
    lastGidRef.current = gid
    setLabel(text)
    setVisible(true)
    setIndeterminate(true)
    setPercent(0)
    setExtra("")
  
    intervalRef.current = window.setInterval(async () => {
      try {
        const p = await apiProgress(gid)
  
        // si pas d'engine -> on ne force rien ici (la barre reste visible jusqu'à stop())
        if (!p.engine) return
  
        // 1) priorité aux simulations (MCTS sim-capped)
        if (p.sims_done != null && p.sims_target && p.sims_target > 0) {
          const ratio = Math.min(0.99, (p.sims_done as number) / (p.sims_target as number))
          setPercent(ratio)
          setIndeterminate(false)
          setExtra(`${p.sims_done!.toLocaleString()} / ${p.sims_target!.toLocaleString()} sims`)
        }
        // 2) sinon temps (Minimax time-capped OU MCTS time-capped)
        else if (p.elapsed_ms != null && p.time_ms && p.time_ms > 0) {
          const ratio = Math.min(0.99, (p.elapsed_ms as number) / (p.time_ms as number))
          setPercent(ratio)
          setIndeterminate(false)
          setExtra(`${Math.round(p.elapsed_ms!)}ms / ${p.time_ms}ms`)
        }
        // 3) sinon indéterminé
        else {
          setIndeterminate(true)
          setExtra("")
        }
      } catch {
        // ignore
      }
    }, 150)
  }

  // cleanup si le composant est démonté
  useEffect(() => () => clearTimer(), [])

  return { visible, label, percent, indeterminate, extra, start, stop }
}

function ProgressFooter(props: {
  visible: boolean
  label: string
  percent: number
  indeterminate: boolean
  extra?: string
}) {
  if (!props.visible) return null
  const pct = Math.round(props.percent * 100)
  return (
    <div className="progress-footer">
      <div className="progress-card">
        <div className="progress-head">
          <span className="spinner-dot" />
          <span>{props.label}{props.extra ? ` — ${props.extra}` : ""}{!props.indeterminate ? ` — ${pct}%` : ""}</span>
        </div>
        <div className={"progress-bar " + (props.indeterminate ? "progress-indeterminate" : "")}>
          <div className="progress-fill" style={props.indeterminate ? {} : { width: `${pct}%` }} />
        </div>
      </div>
    </div>
  )
}
/* ======================================================================== */

export default function App() {
  const [mode, setMode] = useState<Mode>("hvb")

  const [gid, setGid] = useState<string>("")
  const [state, setState] = useState<GameState | null>(null)
  const [phase, setPhase] = useState<BoardPhase>("place")
  const [selectedCell, setSelectedCell] = useState<Coord | null>(null)
  const [selectedQuadrant, setSelectedQuadrant] = useState<Q | null>(null)
  const [anim, setAnim] = useState<{ q: Q; dir: D; stage: "rotating" | "reset" } | null>(null)

  // HVB: choix moteur + params par moteur (pas de doublon ailleurs)
  const [engine, setEngine] = useState<EngineId>("minimax")
  const [mmDepth, setMmDepth] = useState<number>(3)
  const [mmTimeMs, setMmTimeMs] = useState<number | undefined>(undefined)
  const [mcSims, setMcSims] = useState<number>(2000)
  const [mcTimeMs, setMcTimeMs] = useState<number | undefined>(undefined)

  // IA vs IA
  const [showBvbModal, setShowBvbModal] = useState(false)
  const [botBlack, setBotBlack] = useState<BotCfg>({ engine: "minimax", mmDepth: 3, mcSims: 3000 })
  const [botWhite, setBotWhite] = useState<BotCfg>({ engine: "mcts", mmDepth: 3, mcSims: 5000 })

  const [busy, setBusy] = useState(false)
  const [error, setError] = useState("")
  const [human, setHuman] = useState<"B" | "W">("B")
  const [showColorModal, setShowColorModal] = useState(false)
  const [showEngineModal, setShowEngineModal] = useState(false)

  const bot = human === "B" ? "W" : "B"

  // barre de progression (basée sur /progress/{gid})
  const progress = useProgressPolling()

  useEffect(() => {
    apiNew().then(res => { setGid(res.game_id); setState(res.state); setError("") }).catch(() => setError("init"))
  }, [])

  const win = useMemo(() => state ? winningCells(state.grid) : null, [state])
  const bgClass = state ? (mode === "hvb" ? (state.to_move === human ? "bg-human" : "bg-bot") : "bg-neutral") : "bg-neutral"
  const canHoverTiles = !!state && !state.terminal && state.to_move === human && phase === "place" && mode === "hvb"

  function engineTitle(id: EngineId) { return ENGINES.find(e => e.id === id)?.title || id }

  function onCellClick(r: number, c: number) {
    if (mode !== "hvb") return
    if (busy || !state || state.terminal) return
    if (state.to_move !== human) return
    if (phase !== "place") return
    if (state.grid[r][c] !== 0) return
    setSelectedCell({ r, c })
    setSelectedQuadrant(null)
    setPhase("rotate")
  }

  function onQuadrantClick(q: Q) {
    if (mode !== "hvb") return
    if (busy || !state || state.terminal) return
    if (phase !== "rotate") return
    setSelectedQuadrant(q)
  }

  async function onRotate(dir: D) {
    if (mode !== "hvb") return
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

  // ---- BOT calls ----------------------------------------------------------
  function depthFromSims(sims: number) {
    // même mapping que le serveur (sims ≈ depth*500, min 200)
    return Math.max(1, Math.round(sims / 500))
  }
// CHANGÉ : renvoie { depth, timeMs, engine, simulations? }
function hvbCallParams(): BotPost {
  if (engine === "minimax") {
    return { depth: mmDepth, timeMs: mmTimeMs, engine }
  }
  if (engine === "mcts") {
    if (mcTimeMs == null) {
      // sim-capped → on envoie explicitement 'simulations'
      return { depth: Math.max(1, Math.round(mcSims / 500)), simulations: mcSims, engine }
    }
    // time-capped
    return { depth: Math.max(1, Math.round(mcSims / 500)), timeMs: mcTimeMs, engine }
  }
  return { depth: 2, engine }
}

function bvbCallParams(cfg: BotCfg): BotPost {
  if (cfg.engine === "minimax") {
    return { depth: cfg.mmDepth, timeMs: cfg.mmTimeMs, engine: cfg.engine }
  }
  if (cfg.engine === "mcts") {
    if (cfg.mcTimeMs == null) {
      return { depth: Math.max(1, Math.round(cfg.mcSims / 500)), simulations: cfg.mcSims, engine: cfg.engine }
    }
    return { depth: Math.max(1, Math.round(cfg.mcSims / 500)), timeMs: cfg.mcTimeMs, engine: cfg.engine }
  } 
  return { depth: 2, engine: cfg.engine }
}

async function triggerBotHVB() {
  if (mode !== "hvb") return
  if (busy || !state || state.terminal) return
  if (state.to_move !== bot) return

  setBusy(true)
  setError("")
  try {
    const p = hvbCallParams()
    const who = state?.to_move === "B" ? "Noir" : "Blanc"

    // Barre visible si MCTS ou Minimax avec time budget
    if (p.engine === "mcts" || (p.engine === "minimax" && p.timeMs && p.timeMs > 0)) {
      progress.start(gid, `IA (${engineTitle(p.engine)}) — ${who}`)
    }

    const res = await apiBot(gid, p)
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
        progress.stop()
      }, 320)
    }, 0)
  } catch {
    setBusy(false)
    setError("bot")
    progress.stop()
  }
}
async function triggerBotBVB() {
  if (mode !== "bvb") return
  if (busy || !state || state.terminal) return

  const side = state.to_move
  const cfg = side === "B" ? botBlack : botWhite
  const p = bvbCallParams(cfg)
  const who = side === "B" ? "Noir" : "Blanc"

  if (p.engine === "mcts" || (p.engine === "minimax" && p.timeMs && p.timeMs > 0)) {
    progress.start(gid, `IA (${engineTitle(p.engine)}) — ${who}`)
  }

  setBusy(true)
  setError("")
  try {
    const res = await apiBot(gid, p)
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
        progress.stop()
      }, 320)
    }, 0)
  } catch {
    setBusy(false)
    setError("bot")
    progress.stop()
  }
}

  useEffect(() => {
    if (!state || state.terminal) return
    if (mode === "hvb") {
      if (state.to_move === bot && !busy) triggerBotHVB()
    } else {
      if (!busy) triggerBotBVB()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [state, busy, mode, bot, engine, mmDepth, mmTimeMs, mcSims, mcTimeMs, botBlack, botWhite])

  // ---- New games ----------------------------------------------------------
  async function startNewHVB(h: "B" | "W") {
    if (busy) return
    setMode("hvb")
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
        if (res.state.to_move !== h) triggerBotHVB()
      }, 0)
    } finally {
      setBusy(false)
    }
  }

  async function startNewBVB() {
    if (busy) return
    setMode("bvb")
    setShowBvbModal(false)
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
      setTimeout(() => { triggerBotBVB() }, 0)
    } finally {
      setBusy(false)
    }
  }

  // ---- UI helpers ---------------------------------------------------------
  function openNewGameModal() {
    if (busy) return
    setShowColorModal(true)
  }
  function openBvbModal() {
    if (busy) return
    setShowBvbModal(true)
  }
  function winnerLabel() {
    if (!state || !state.terminal) return ""
    if (!state.winner) return "Match nul"
    if (mode === "bvb") {
      const side = state.winner
      const botTitle = side === "B" ? engineTitle(botBlack.engine) : engineTitle(botWhite.engine)
      const color = side === "B" ? "Noir" : "Blanc"
      return `Victoire : ${botTitle} (${color})`
    } else {
      const who = state.winner === human ? "Tu gagnes" : "L’IA gagne"
      return who
    }
  }
  function botSummary(cfg: BotCfg) {
    if (cfg.engine === "minimax") {
      return `Minimax — profondeur ${cfg.mmDepth}${cfg.mmTimeMs ? `, ${cfg.mmTimeMs}ms` : ""}`
    } else if (cfg.engine === "mcts") {
      return `MCTS — ${cfg.mcSims} simulations${cfg.mcTimeMs ? `, ${cfg.mcTimeMs}ms` : ""}`
    }
    return "Policy (bientôt)"
  }

  const thinkingChip = state && !state.terminal ? (
    <div className="status-chip">
      {busy && <span className="spinner-sm" />}
      {mode === "bvb"
        ? <>Tour IA : {engineTitle(state.to_move === "B" ? botBlack.engine : botWhite.engine)} ({state.to_move === "B" ? "Noir" : "Blanc"})</>
        : <>Au tour de : {state.to_move}{busy && state.to_move !== human ? " • IA réfléchit" : ""}</>}
    </div>
  ) : null

  // ---- Render -------------------------------------------------------------
  return (
    <div className={"min-h-screen w-full " + bgClass}>
      <div className="mx-auto max-w-6xl px-6 py-10">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-3xl font-extrabold tracking-tight drop-shadow-sm">SuperPentago</h1>
          <div className="flex items-center gap-3">
            <button className="btn px-3 py-2 rounded-lg bg-white border border-gray-300 shadow-sm text-sm"
                    onClick={() => setShowEngineModal(true)}
                    disabled={mode !== "hvb"}>
              IA : {engineTitle(engine)}
            </button>
            <button onClick={openNewGameModal} disabled={busy} className="btn px-4 py-2 rounded-lg bg-white border border-gray-300 shadow-sm">New game</button>
            <button onClick={openBvbModal} disabled={busy} className="btn px-4 py-2 rounded-lg bg-white border border-gray-300 shadow-sm">IA vs IA</button>
          </div>
        </div>

        {thinkingChip}

        {state && (
          <div className="relative grid grid-cols-1 md:grid-cols-[auto_320px] gap-8">
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

            {/* Panneau paramètres : moteur unique visible ici */}
            <div className="bg-white rounded-2xl border border-gray-200 shadow p-4 flex flex-col gap-3">
              {mode === "hvb" ? (
                <>
                  <div className="text-sm font-semibold">Paramètres IA (adverse)</div>
                  <div className="text-sm">Moteur : {engineTitle(engine)}</div>

                  {engine === "minimax" && (
                    <>
                      <label className="text-sm">Profondeur</label>
                      <input
                        type="range"
                        min={1}
                        max={8}
                        value={mmDepth}
                        onChange={(e) => setMmDepth(parseInt(e.target.value || "3"))}
                      />
                      <div className="text-xs text-gray-600">Actuelle : {mmDepth}</div>

                      <label className="text-sm mt-2">Temps (ms, optionnel)</label>
                      <input
                        type="number"
                        className="border border-gray-300 rounded px-2 py-1"
                        value={mmTimeMs ?? ""}
                        placeholder="ms"
                        onChange={e => setMmTimeMs(e.target.value === "" ? undefined : parseInt(e.target.value))}
                      />
                    </>
                  )}

                  {engine === "mcts" && (
                    <>
                      <label className="text-sm">Simulations</label>
                      <input
                        type="number"
                        className="border border-gray-300 rounded px-2 py-1"
                        min={200}
                        step={100}
                        value={mcSims}
                        onChange={e => setMcSims(parseInt(e.target.value || "200"))}
                      />
                      <div className="text-xs text-gray-600">
                        Conseil : 200–20 000 (plus = plus fort, plus lent)
                      </div>

                      <label className="text-sm mt-2">Temps (ms, optionnel)</label>
                      <input
                        type="number"
                        className="border border-gray-300 rounded px-2 py-1"
                        value={mcTimeMs ?? ""}
                        placeholder="ms"
                        onChange={e => setMcTimeMs(e.target.value === "" ? undefined : parseInt(e.target.value))}
                      />
                    </>
                  )}

                  {engine === "policy" && (
                    <div className="text-xs text-gray-600">Bientôt disponible.</div>
                  )}

                  <div className="text-xs break-all text-gray-500 mt-2">Game ID: {gid}</div>
                </>
              ) : (
                <>
                  <div className="text-sm font-semibold">Match IA vs IA</div>
                  <div className="text-sm">Noir : {botSummary(botBlack)}</div>
                  <div className="text-sm">Blanc : {botSummary(botWhite)}</div>
                  <div className="text-xs break-all text-gray-500">Game ID: {gid}</div>
                </>
              )}
            </div>
          </div>
        )}

        {state?.terminal && (
          <div className="modal-backdrop">
            <div className="modal">
              <div className="modal-title">{winnerLabel()}</div>
              <div className="modal-actions">
                <button className="btn-choice" onClick={openNewGameModal}>Nouvelle partie</button>
                <button className="btn-choice" onClick={openBvbModal}>Relancer IA vs IA</button>
              </div>
            </div>
          </div>
        )}

        {showColorModal && (
          <div className="modal-backdrop">
            <div className="modal" onClick={(e)=>e.stopPropagation()}>
              <div className="modal-title">Choisis ta couleur</div>
              <div className="modal-actions">
                <button className="btn-choice btn-black" onClick={() => startNewHVB("B")}>Noir</button>
                <button className="btn-choice btn-white" onClick={() => startNewHVB("W")}>Blanc</button>
              </div>
              <div className="ai-note">Le moteur sélectionné sera utilisé pour l’adversaire.</div>
              <div className="modal-footer">
                <button className="btn-cancel" onClick={() => setShowColorModal(false)}>Annuler</button>
              </div>
            </div>
          </div>
        )}

        {showEngineModal && (
          <div className="modal-backdrop" onClick={() => setShowEngineModal(false)}>
            <div className="modal" onClick={(e) => e.stopPropagation()}>
              <div className="modal-title">Choisir l’IA (Joueur vs IA)</div>
              <div className="ai-note">Sélectionne le moteur utilisé par l’IA adverse.</div>
              <div className="ai-grid">
                {ENGINES.map(e => (
                  <div key={e.id} className={"ai-card " + (!e.ready ? "disabled" : "")}>
                    <div className="ai-title">{e.title}</div>
                    <div className="ai-desc">{e.desc}</div>
                    {!e.ready && <div className="ai-badge">Bientôt</div>}
                    {e.ready && (
                      <button
                        className="choose"
                        onClick={() => { setEngine(e.id); setShowEngineModal(false) }}
                      >Sélectionner</button>
                    )}
                  </div>
                ))}
              </div>
              <div className="modal-footer">
                <button className="btn-cancel" onClick={() => setShowEngineModal(false)}>Fermer</button>
              </div>
            </div>
          </div>
        )}

        {showBvbModal && (
          <div className="modal-backdrop" onClick={() => setShowBvbModal(false)}>
            <div className="modal" onClick={(e) => e.stopPropagation()}>
              <div className="modal-title">Configurer IA vs IA</div>
              <div className="ai-note">Choisis un moteur et ses paramètres pour chaque couleur, puis lance le match.</div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Noir */}
                <div className="ai-card">
                  <div className="ai-title">Noir</div>
                  <select
                    className="border border-gray-300 rounded px-2 py-2"
                    value={botBlack.engine}
                    onChange={(e) => setBotBlack({ ...botBlack, engine: e.target.value as EngineId })}
                  >
                    {ENGINES.map(e => <option key={e.id} value={e.id} disabled={!e.ready}>{e.title}</option>)}
                  </select>

                  {botBlack.engine === "minimax" && (
                    <>
                      <label className="text-sm">Profondeur</label>
                      <input
                        type="number"
                        className="border border-gray-300 rounded px-2 py-1"
                        value={botBlack.mmDepth}
                        min={1}
                        onChange={e => setBotBlack({ ...botBlack, mmDepth: parseInt(e.target.value || "1") })}
                      />
                      <label className="text-sm mt-2">Temps (ms, optionnel)</label>
                      <input
                        type="number"
                        className="border border-gray-300 rounded px-2 py-1"
                        value={botBlack.mmTimeMs ?? ""}
                        placeholder="ms"
                        onChange={e => setBotBlack({ ...botBlack, mmTimeMs: e.target.value === "" ? undefined : parseInt(e.target.value) })}
                      />
                    </>
                  )}
                  {botBlack.engine === "mcts" && (
                    <>
                      <label className="text-sm">Simulations</label>
                      <input
                        type="number"
                        className="border border-gray-300 rounded px-2 py-1"
                        value={botBlack.mcSims}
                        min={200}
                        step={100}
                        onChange={e => setBotBlack({ ...botBlack, mcSims: parseInt(e.target.value || "200") })}
                      />
                      <label className="text-sm mt-2">Temps (ms, optionnel)</label>
                      <input
                        type="number"
                        className="border border-gray-300 rounded px-2 py-1"
                        value={botBlack.mcTimeMs ?? ""}
                        placeholder="ms"
                        onChange={e => setBotBlack({ ...botBlack, mcTimeMs: e.target.value === "" ? undefined : parseInt(e.target.value) })}
                      />
                    </>
                  )}
                </div>

                {/* Blanc */}
                <div className="ai-card">
                  <div className="ai-title">Blanc</div>
                  <select
                    className="border border-gray-300 rounded px-2 py-2"
                    value={botWhite.engine}
                    onChange={(e) => setBotWhite({ ...botWhite, engine: e.target.value as EngineId })}
                  >
                    {ENGINES.map(e => <option key={e.id} value={e.id} disabled={!e.ready}>{e.title}</option>)}
                  </select>

                  {botWhite.engine === "minimax" && (
                    <>
                      <label className="text-sm">Profondeur</label>
                      <input
                        type="number"
                        className="border border-gray-300 rounded px-2 py-1"
                        value={botWhite.mmDepth}
                        min={1}
                        onChange={e => setBotWhite({ ...botWhite, mmDepth: parseInt(e.target.value || "1") })}
                      />
                      <label className="text-sm mt-2">Temps (ms, optionnel)</label>
                      <input
                        type="number"
                        className="border border-gray-300 rounded px-2 py-1"
                        value={botWhite.mmTimeMs ?? ""}
                        placeholder="ms"
                        onChange={e => setBotWhite({ ...botWhite, mmTimeMs: e.target.value === "" ? undefined : parseInt(e.target.value) })}
                      />
                    </>
                  )}
                  {botWhite.engine === "mcts" && (
                    <>
                      <label className="text-sm">Simulations</label>
                      <input
                        type="number"
                        className="border border-gray-300 rounded px-2 py-1"
                        value={botWhite.mcSims}
                        min={200}
                        step={100}
                        onChange={e => setBotWhite({ ...botWhite, mcSims: parseInt(e.target.value || "200") })}
                      />
                      <label className="text-sm mt-2">Temps (ms, optionnel)</label>
                      <input
                        type="number"
                        className="border border-gray-300 rounded px-2 py-1"
                        value={botWhite.mcTimeMs ?? ""}
                        placeholder="ms"
                        onChange={e => setBotWhite({ ...botWhite, mcTimeMs: e.target.value === "" ? undefined : parseInt(e.target.value) })}
                      />
                    </>
                  )}
                </div>
              </div>

              <div className="modal-actions">
                <button className="btn-choice" onClick={startNewBVB}>Lancer le match</button>
              </div>
              <div className="modal-footer">
                <button className="btn-cancel" onClick={() => setShowBvbModal(false)}>Fermer</button>
              </div>
            </div>
          </div>
        )}

      </div>

      {/* Barre de progression (bas de page) */}
      <ProgressFooter
        visible={progress.visible}
        label={progress.label}
        percent={progress.percent}
        indeterminate={progress.indeterminate}
        extra={progress.extra}
      />
    </div>
  )
}