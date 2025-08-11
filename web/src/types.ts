export type Grid = number[][];
export type GameState = {
  grid: Grid;
  to_move: "B" | "W";
  terminal: boolean;
  winner: "B" | "W" | null;
};

export type NewGameResponse = {
  game_id: string;
  state: GameState;
};

export type StateResponse = {
  state: GameState;
};

export type BotMoveResponse = {
  move: string;
  state: GameState;
  engine: "minimax" | "mcts";
};