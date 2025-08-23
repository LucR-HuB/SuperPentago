// web/src/api.ts
import type { NewGameResponse, StateResponse, BotMoveResponse } from "./types"
const BASE = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000"

export async function apiNew(): Promise<NewGameResponse> {
  const r = await fetch(`${BASE}/new`, { method: "POST" })
  if (!r.ok) throw new Error("new")
  return r.json()
}

export async function apiState(gid: string): Promise<StateResponse> {
  const r = await fetch(`${BASE}/state/${gid}`)
  if (!r.ok) throw new Error("state")
  return r.json()
}

export async function apiPlay(gid: string, cell: string, quadrant: string, direction: string): Promise<StateResponse> {
  const r = await fetch(`${BASE}/play/${gid}`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ cell, quadrant, direction }),
  })
  if (!r.ok) throw new Error("play")
  return r.json()
}

// ✅ NOUVELLE SIGNATURE: on prend un objet camelCase et on mappe vers snake_case
export async function apiBot(
  gid: string,
  opts: { depth: number; engine?: "minimax" | "mcts" | "policy"; timeMs?: number; simulations?: number }
): Promise<BotMoveResponse> {
  const body = {
    depth: opts.depth,
    engine: opts.engine,
    time_ms: opts.timeMs,          // <-- mapping camel → snake
    simulations: opts.simulations, // <-- idem
  }
  const r = await fetch(`${BASE}/bot/${gid}`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  })
  if (!r.ok) throw new Error("bot")
  return r.json()
}

export type ProgressState = {
  engine: "minimax" | "mcts" | "policy" | null
  done: boolean
  elapsed_ms?: number
  time_ms?: number | null
  sims_target?: number | null
  sims_done?: number | null
  percent?: number | null
}

export async function apiProgress(gid: string): Promise<ProgressState> {
  const r = await fetch(`${BASE}/progress/${gid}`)
  if (!r.ok) throw new Error("progress")
  return r.json()
}