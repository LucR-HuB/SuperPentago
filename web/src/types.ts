export type Grid = number[][]
export type ToMove = "B" | "W"

export type GameState = {
  grid: Grid
  to_move: ToMove
  terminal: boolean
  winner: ToMove | null
}

export type NewGameResponse = {
  game_id: string
  state: GameState
}

export type StateResponse = {
  state: GameState
}

export type BotMoveResponse = {
  state: GameState
  move: string
}