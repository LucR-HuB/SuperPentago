import type { NewGameResponse, StateResponse, BotMoveResponse } from "./types";

const BASE = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

export async function apiNew(): Promise<NewGameResponse> {
  const r = await fetch(`${BASE}/new`, { method: "POST" });
  if (!r.ok) throw new Error("new");
  return r.json();
}

export async function apiState(gid: string): Promise<StateResponse> {
  const r = await fetch(`${BASE}/state/${gid}`);
  if (!r.ok) throw new Error("state");
  return r.json();
}

export async function apiPlay(
  gid: string,
  cell: string,
  quadrant: string,
  direction: string
): Promise<StateResponse> {
  const r = await fetch(`${BASE}/play/${gid}`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ cell, quadrant, direction }),
  });
  if (!r.ok) throw new Error("play");
  return r.json();
}

export async function apiBot(
  gid: string,
  depth: number,
  time_ms?: number,
  engine: "minimax" | "mcts" | "policy" = "minimax"
): Promise<BotMoveResponse> {
  const r = await fetch(`${BASE}/bot/${gid}`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ depth, time_ms, engine }),
  });
  if (!r.ok) throw new Error("bot");
  return r.json();
}