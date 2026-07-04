"""ASCII constellation art with the brand name centered — Grok CLI style.

Renders a starfield of faint dots with "BITTU" (or any brand) in the middle,
matching the reference screenshot's centered constellation logo.
"""
from __future__ import annotations
import random

from rich.text import Text


def constellation(brand: str = "BITTU", width: int = 60, height: int = 9,
                  seed: int = 7) -> Text:
    """Build a Rich Text starfield with the brand word centered.

    Deterministic (seeded) so it looks the same every launch, like the ref.
    """
    rng = random.Random(seed)
    grid = [[" " for _ in range(width)] for _ in range(height)]

    # Scatter faint stars: mix of '.', '*', '·' at low density.
    star_chars = [".", "·", "*", "✦", "˙"]
    density = int(width * height * 0.06)
    for _ in range(density):
        r = rng.randint(0, height - 1)
        c = rng.randint(0, width - 1)
        grid[r][c] = rng.choice(star_chars)

    # Clear a horizontal band in the middle for the brand word.
    mid = height // 2
    start = (width - len(brand)) // 2
    for c in range(max(0, start - 3), min(width, start + len(brand) + 3)):
        grid[mid][c] = " "

    # Build the Text with styling: brand bright, stars dim.
    out = Text()
    for r in range(height):
        for c in range(width):
            ch = grid[r][c]
            if ch == " ":
                out.append(" ")
            else:
                out.append(ch, style="#6b6b6b")
        out.append("\n")

    # Overlay the brand word onto the middle row, centered & bright.
    lines = out.plain.split("\n")
    row = list(lines[mid].ljust(width))
    for i, ch in enumerate(brand):
        if start + i < width:
            row[start + i] = ch
    lines[mid] = "".join(row)

    # Rebuild with per-char styling (brand = bold white, rest = dim stars).
    styled = Text()
    for ri, line in enumerate(lines[:height]):
        for ci, ch in enumerate(line):
            if ri == mid and start <= ci < start + len(brand):
                styled.append(ch, style="bold white")
            elif ch != " ":
                styled.append(ch, style="#6b6b6b")
            else:
                styled.append(" ")
        styled.append("\n")
    return styled
