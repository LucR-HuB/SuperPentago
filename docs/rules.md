# Pentago — Rules Specification
Version: 1.0  
Status: Stable

## 1. Components and Coordinates
- Board is **6 × 6**, divided into **4 quadrants** of **3 × 3** each:
  - `Q00`: rows 1–3, columns A–C (top-left)
  - `Q01`: rows 1–3, columns D–F (top-right)
  - `Q10`: rows 4–6, columns A–C (bottom-left)
  - `Q11`: rows 4–6, columns D–F (bottom-right)
- Two players: **Black** and **White**. **Black moves first**.
- Coordinates:
  - Columns **A–F** from left to right.
  - Rows **1–6** from top to bottom.
  - A square is addressed as `[A-F][1-6]` (e.g., `E5`).

## 2. Turn Structure
A turn **always** consists of two actions, in this order:
1. **Place** one marble of your color on **an empty square**.
2. **Rotate** **one** quadrant (`Q00`, `Q01`, `Q10`, `Q11`) by **+90° (CW)** or **–90° (CCW)**.

Execution notes:
- The rotation is **mandatory**, even if the quadrant is symmetric and the resulting board looks unchanged.
- **180° rotations** and skipping rotation are **not allowed**.

## 3. Win Condition
- A player wins **immediately after the rotation** if they have **at least 5** marbles **consecutively aligned** in a **horizontal**, **vertical**, or **diagonal** line on the **6 × 6** grid (alignments may cross quadrant borders).
- Alignments are checked **only after the rotation** of the current turn (an alignment created by the placement but broken by the rotation **does not count**).

## 4. Simultaneous Alignments
- If **after the same rotation** both players have a valid alignment (≥ 5), **the player who just completed the turn wins**.

## 5. Draw
- The game is a **draw** if **all 36 squares** are occupied **and** no player satisfied the win condition (Section 3) during the last turn.

## 6. Legal Moves
A move is legal if and only if:
- The placement square is **empty**.
- **Exactly one** quadrant is **rotated** by **±90°** immediately after the placement.
- No other constraints apply (no captures, no “gravity”).

## 7. Canonical Move Notation
- Format: `<Placement> <Quadrant> <Direction>`
  - `Placement`: `[A-F][1-6]` (e.g., `E5`)
  - `Quadrant`: `Q00 | Q01 | Q10 | Q11`
  - `Direction`: `CW` (clockwise, +90°) | `CCW` (counterclockwise, –90°)
- Example: `E5 Q01 CW`

## 8. Technical Indexing (Implementation Reference)
- Recommended internal indices:
  - Rows `r ∈ {0..5}` from top (0) to bottom (5).
  - Columns `c ∈ {0..5}` from left (0) to right (5).
  - Quadrant ranges:
    - `Q00`: `r ∈ {0,1,2}`, `c ∈ {0,1,2}`
    - `Q01`: `r ∈ {0,1,2}`, `c ∈ {3,4,5}`
    - `Q10`: `r ∈ {3,4,5}`, `c ∈ {0,1,2}`
    - `Q11`: `r ∈ {3,4,5}`, `c ∈ {3,4,5}`
- A `CW` rotation applies **+90°** to the quadrant’s 3×3 submatrix; `CCW` applies **–90°**.

## 9. Explicitly Excluded Variants
- **Optional rotation** (including on the last move): **no**.
- Win condition **before** rotation (after placement only): **no**.
- **180° rotation**: **no**.
- Alternate openings (e.g., initial placement without rotation): **no**.

## 10. Game Termination
The game ends as soon as one of the following holds:
1. **Win** condition (Section 3) after a full turn.
2. **Draw** (Section 5).